"""Materialized public pages and an at-least-once IndexNow outbox."""
import hashlib, os, re
from datetime import timedelta
from urllib.parse import urlsplit, quote
from xml.sax.saxutils import escape
import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from fastapi import HTTPException
from .db import Session, Scan, PublicScore, IndexNotification, now
from .config import BASE, PUBLIC_URL, CONTROLLER, CONTACT

BOTS=['*','GPTBot','OAI-SearchBot','ClaudeBot','Claude-SearchBot','PerplexityBot','Google-Extended','CCBot']
def domain_name(value):
    value=value.lower().rstrip('.').encode('idna').decode('ascii')
    if len(value)>253 or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',value) or '..' in value:
        raise ValueError('Invalid domain')
    return value

def publish_scan(db, scan):
    if not scan.public or scan.status!='completed' or not scan.report:return
    domain=domain_name(urlsplit(scan.url).hostname)
    # A per-domain row lock serializes concurrent snapshot updates in PostgreSQL.
    from sqlalchemy.dialects.postgresql import insert
    if db.bind.dialect.name=='postgresql':
        db.execute(insert(PublicScore).values(domain=domain,payload={},html='',updated_at=now()).on_conflict_do_nothing())
    record=db.scalar(select(PublicScore).where(PublicScore.domain==domain).with_for_update())
    rows=db.scalars(select(Scan).where(Scan.public==True,Scan.status=='completed').order_by(Scan.created_at.desc(),Scan.id)).all()
    rows=[r for r in rows if domain_name(urlsplit(r.url).hostname)==domain and r.report]
    if not rows:return
    latest=rows[0];r=latest.report
    history=[{'id':x.id,'url':x.url,'scanned_at':x.report['scanned_at'],'score':x.report['score'],'coverage':x.report['coverage'],'methodology_version':x.report['methodology_version']} for x in rows]
    answer=f"{domain} scored {r['score']}/100 for agent readiness on {r['scanned_at']}." if r['score'] is not None else f"{domain} does not yet have a complete agent-readiness score; measurement coverage is {r['coverage']}%."
    payload={'domain':domain,'answer':answer,'canonical':PUBLIC_URL+'/score/'+domain,'scan':{'id':latest.id,'url':latest.url,'public':True,'status':'completed','report':r,'error':None},'history':history}
    title=f'Is {domain} agent-ready?'
    structured={'@context':'https://schema.org','@type':'WebPage','name':title,'url':payload['canonical'],'description':answer,'dateModified':r['scanned_at']}
    env=Environment(loader=FileSystemLoader(BASE/'templates'),autoescape=select_autoescape())
    rendered=env.get_template('public-score.html').render(title=title,base_url=PUBLIC_URL,controller=CONTROLLER or 'Operator details required before public launch',contact=CONTACT,structured=structured,**payload)
    if not record:record=PublicScore(domain=domain);db.add(record)
    record.payload=payload;record.html=rendered;record.updated_at=now()
    revision=hashlib.sha256(rendered.encode()).hexdigest()
    key=hashlib.sha256((payload['canonical']+revision).encode()).hexdigest()
    if not db.get(IndexNotification,key):db.add(IndexNotification(id=key,url=payload['canonical']))

def public_score(domain):
    with Session() as db:
        row=db.get(PublicScore,domain_name(domain))
        if not row:raise HTTPException(404,'No published completed scan for this domain')
        return row.payload

def robots_text():
    exclusions=['/scans/','/benchmark/runs/','/api/v1/billing/','/mcp']
    return '\n\n'.join('User-agent: '+bot+'\nAllow: /\n'+'\n'.join('Disallow: '+x for x in exclusions) for bot in BOTS)+'\n\nSitemap: '+PUBLIC_URL+'/sitemap.xml\n'

def sitemap(paths):
    with Session() as db:rows=db.scalars(select(PublicScore).order_by(PublicScore.domain)).all()
    entries=[(PUBLIC_URL+p,None) for p in paths]+[(x.payload['canonical'],x.updated_at.isoformat()) for x in rows]
    # Sitemap index/shards keep the protocol limit below 50,000 URLs per file.
    return entries

def urlset(entries):
    return '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+escape(url)+'</loc>'+('<lastmod>'+escape(stamp)+'</lastmod>' if stamp else '')+'</url>' for url,stamp in entries)+'</urlset>'

def index_key():
    key=os.getenv('INDEXNOW_KEY','')
    return key if re.fullmatch(r'[a-zA-Z0-9-]{8,128}',key) else None

async def notify_indexnow():
    key=index_key();host=urlsplit(PUBLIC_URL).hostname
    if not key or not PUBLIC_URL.startswith('https://') or not host or host in ('localhost','example.com'):return
    with Session() as db:
        jobs=db.scalars(select(IndexNotification).where(IndexNotification.accepted==False,IndexNotification.next_attempt<=now()).limit(100)).all()
        ids=[j.id for j in jobs];urls=list(dict.fromkeys(j.url for j in jobs if urlsplit(j.url).netloc==urlsplit(PUBLIC_URL).netloc))
    if not urls:return
    try:
        async with httpx.AsyncClient(timeout=15,follow_redirects=False) as client:
            response=await client.post('https://api.indexnow.org/indexnow',json={'host':host,'key':key,'keyLocation':PUBLIC_URL+'/indexnow-key.txt','urlList':urls})
            status=response.status_code
    except httpx.HTTPError:status=0
    with Session.begin() as db:
        for id in ids:
            job=db.get(IndexNotification,id);job.attempts+=1;job.last_status=status
            job.accepted=status in (200,202) # Receipt, not proof of indexing.
            job.next_attempt=now()+timedelta(seconds=min(86400,60*2**min(job.attempts,10)))

def queue_reference_pages():
    """Called on worker startup; changing RELEASE_ID schedules updated documentation."""
    from .main import sitemap_entries
    revision=os.getenv('RELEASE_ID','0.1.0-discovery')
    with Session.begin() as db:
        for url,_ in sitemap_entries():
            key=hashlib.sha256((url+revision).encode()).hexdigest()
            if not db.get(IndexNotification,key):db.add(IndexNotification(id=key,url=url))
