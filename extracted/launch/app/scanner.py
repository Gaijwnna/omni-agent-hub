import hashlib, json, re, asyncio
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
import httpx
from .network import fetch, fetch_page, robots, text, validate_url, FetchError
from .config import RENDERER_URL
from .db import now

VERSION='readiness-1.0.0'
WEIGHTS={'semantics':20,'labels':15,'layout_stability':15,'captcha':10,'llms_txt':5,'robots':10,'initial_html':15,'api_discovery':10}
FIXES={
 'semantics':'Use a main landmark, one descriptive h1, native buttons and table headers.',
 'labels':'Give each input a non-empty associated label, aria-label or resolvable aria-labelledby.',
 'layout_stability':'Reserve space for assets and avoid moving controls. Retest under the published viewport and observation window.',
 'captcha':'Offer a documented, rate-limited API or accessible alternative. Do not weaken abuse prevention.',
 'llms_txt':'Publish a useful text/markdown llms.txt with links to authoritative documentation.',
 'robots':'Document deliberate crawler policy. This check reports access policy, not a recommendation to admit every crawler.',
 'initial_html':'Server-render useful content and data rather than returning an empty application shell.',
 'api_discovery':'Expose valid OpenAPI or a capabilities manifest and link the API from your HTML.'}
AGENTS=['OmniAgentScanner','GPTBot','OAI-SearchBot','ChatGPT-User','ClaudeBot','Claude-User','Google-Extended']

def visible_text(soup):
    for node in soup(['script','style','template','noscript']): node.decompose()
    return ' '.join(soup.stripped_strings)

def labelled(el,soup):
    if el.get('aria-label','').strip():return True
    refs=el.get('aria-labelledby','').split()
    if refs and all(soup.find(id=r) and soup.find(id=r).get_text(strip=True) for r in refs):return True
    if el.get('id'):
        label=soup.find('label',attrs={'for':el['id']})
        if label and label.get_text(strip=True):return True
    parent=el.find_parent('label')
    return bool(parent and parent.get_text(strip=True))

def analyse(html, auxiliary, browser=None):
    soup=BeautifulSoup(html,'html.parser');h1=soup.find_all('h1');tables=soup.find_all('table')
    semantics=[bool(soup.find('main') or soup.find(attrs={'role':'main'})),len(h1)==1,not soup.select('div[onclick],span[onclick]'),all(t.find('th') for t in tables)]
    controls=[e for e in soup.select('input,select,textarea') if e.get('type','').lower() not in ('hidden','submit','button','reset','image')]
    good=sum(labelled(e,soup) for e in controls)
    markup_captcha=bool(soup.select('[class*="g-recaptcha"],[class*="h-captcha"],[class*="cf-turnstile"],iframe[src*="recaptcha"],iframe[src*="hcaptcha"],script[src*="recaptcha"],script[src*="turnstile"]'))
    raw_text=visible_text(BeautifulSoup(html,'html.parser'));rendered=(browser or {}).get('text_characters')
    ratio=min(1,len(raw_text)/max(rendered,1)) if rendered is not None else None
    checks=[]
    def add(name,value,evidence):checks.append({'id':name,'weight':WEIGHTS[name],'earned':None if value is None else round(max(0,min(1,value))*WEIGHTS[name],2),'status':'unknown' if value is None else ('pass' if value==1 else 'needs_work'),'evidence':evidence,'fix':FIXES[name]})
    add('semantics',sum(semantics)/len(semantics),{'main':semantics[0],'single_h1':semantics[1],'native_controls':semantics[2],'tables_with_headers':semantics[3]})
    add('labels',good/len(controls) if controls else 1,{'labelled':good,'total':len(controls)})
    cls=(browser or {}).get('cls');add('layout_stability',None if cls is None else (1 if cls<=.1 else .5 if cls<=.25 else 0),{'observed_cls':cls,'window_seconds':5,'scope':'one desktop navigation; not field Core Web Vitals'})
    captcha=markup_captcha or (browser or {}).get('captcha',False);add('captcha',0 if captcha else 1,{'detected':captcha,'method':'known markup/provider patterns; absence is not proof'})
    llms=auxiliary.get('llms');add('llms_txt',None if llms is None else int(llms),{'valid_text_document':llms})
    policies=auxiliary.get('robots');add('robots',None if policies is None else sum(policies.values())/len(policies),{'allowed_at_url':policies,'note':'crawler preferences are policy choices'})
    add('initial_html',ratio,{'raw_text_characters':len(raw_text),'rendered_text_characters':rendered,'raw_to_rendered_ratio':ratio})
    api=auxiliary.get('api');add('api_discovery',None if api is None else int(api),{'valid_manifest_or_openapi':api})
    tested=sum(c['weight'] for c in checks if c['earned'] is not None);earned=sum(c['earned'] or 0 for c in checks)
    return {'methodology_version':VERSION,'score':round(earned) if tested==100 else None,'partial_score':round(earned),'coverage':tested,'score_range':[round(earned),round(earned+100-tested)],'checks':checks,'limitations':['Single URL, one viewport, one observation window. Not a guarantee of task success.','HTTP and rendered evidence may differ by region, authentication and time.','Text content is treated as untrusted input; no model follows page instructions.']}

async def scan(url):
    url=validate_url(url)
    async with asyncio.timeout(65):
        page=await fetch_page(url)
        if page['status']!=200:raise FetchError(f'Target returned HTTP {page["status"]}; no score issued')
        content_type=page['headers'].get('Content-Type',page['headers'].get('content-type',''))
        if 'html' not in content_type:raise FetchError('The target is not an HTML document')
        final=page['url'];p=urlsplit(final);origin=f'{p.scheme}://{p.netloc}'
        async def probe(path,kind):
            try:
                r=await fetch(origin+path,limit=256_000)
                if r['status']==404:return False
                if r['status']!=200:return None
                mime=r['headers'].get('Content-Type',r['headers'].get('content-type',''))
                if kind=='text':return 'html' not in mime and len(text(r).strip())>20
                data=json.loads(text(r))
                return isinstance(data,dict) and (bool(data.get('openapi') and data.get('paths')) if kind=='openapi' else bool(data.get('capabilities') or data.get('tools')))
            except Exception:return None
        llms,openapi,manifest=await asyncio.gather(probe('/llms.txt','text'),probe('/openapi.json','openapi'),probe('/.well-known/agent.json','manifest'))
        policies=None
        try:
            rule,_=await robots(final);policies={agent:rule.can_fetch(agent,final) for agent in AGENTS}
        except Exception:pass
        browser=None;browser_error=None
        if RENDERER_URL:
            try:
                async with httpx.AsyncClient(timeout=40,trust_env=False) as client:
                    r=await client.post(RENDERER_URL+'/render',json={'url':final});r.raise_for_status();browser=r.json()
            except Exception:browser_error='Browser measurement unavailable'
        report=analyse(text(page),{'llms':llms,'api':True if openapi or manifest else (False if openapi is False and manifest is False else None),'robots':policies},browser)
        report.update({'url':final,'scanned_at':now().isoformat(),'html_sha256':hashlib.sha256(page['body']).hexdigest(),'browser':browser,'browser_error':browser_error or (None if browser else 'Browser measurement not configured'),'certified':False})
        return report
