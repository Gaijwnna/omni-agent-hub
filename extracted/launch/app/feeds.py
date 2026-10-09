import json,hashlib,base64,hmac,secrets
from datetime import timedelta
from sqlalchemy import select
from cryptography.fernet import Fernet
from .network import fetch,text,validate_url
from .db import Session,FeedSnapshot,AlertEvent,Subscription,Delivery,now
from .security import require_account,owned
from .config import SECRET

URL='https://environment.data.gov.uk/flood-monitoring/id/floods'
LICENCE='https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'
SOURCE='ea-flood-warnings'
FERNET=Fernet(base64.urlsafe_b64encode(hashlib.sha256(SECRET.encode()).digest()))

def snapshot():
    with Session() as db:
        row=db.get(FeedSnapshot,SOURCE)
        if not row:return {'items':[],'status':'not_yet_fetched','source_url':URL,'licence':LICENCE,'last_fetched':None,'stale':True}
        stamp=row.fetched_at
        if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=now().tzinfo)
        return {**row.payload,'last_fetched':stamp.isoformat(),'stale':now()-stamp>timedelta(minutes=30)}
async def refresh():
    r=await fetch(URL,limit=4_000_000)
    if r['status']!=200:raise ValueError('Environment Agency source unavailable')
    body=json.loads(text(r))
    if not isinstance(body.get('items'),list):raise ValueError('Unexpected source format')
    records=[{'id':i['@id'],'description':i.get('description',''),'severity':i.get('severity',''),'severity_level':i.get('severityLevel'),'source_url':i['@id'],'licence':LICENCE,'updated_at':i.get('timeMessageChanged') or i.get('timeRaised'),'attribution':'Environment Agency flood-monitoring API; contains public sector information licensed under the Open Government Licence v3.0.'} for i in body['items']]
    payload={'items':records,'status':'available','source_url':URL,'licence':LICENCE,'disclaimer':'Not an emergency warning service. Consult official flood warnings for safety decisions.'}
    with Session.begin() as db:
        old=db.get(FeedSnapshot,SOURCE)
        if old and old.payload['items']!=records:
            event=AlertEvent(source=SOURCE,payload={'type':'public_data_changed','source':SOURCE,'previous_count':len(old.payload['items']),'current_count':len(records),'data_url':'/api/v1/signals'});db.add(event);db.flush()
            for sub in db.scalars(select(Subscription).where(Subscription.active==True,Subscription.source==SOURCE,Subscription.webhook!=None)):
                db.add(Delivery(event_id=event.id,subscription_id=sub.id))
        if old:old.payload=payload;old.fetched_at=now()
        else:db.add(FeedSnapshot(id=SOURCE,payload=payload))

def subscribe(source,webhook=None):
    who=require_account()
    if source!=SOURCE:raise ValueError('Only the approved Environment Agency source is enabled; retailer sources require permission review')
    if webhook:
        validate_url(webhook)
        if not webhook.startswith('https://'):raise ValueError('Webhook URL must use HTTPS')
    secret=secrets.token_urlsafe(32) if webhook else None
    sub=Subscription(owner=who.id,source=source,webhook=webhook,secret_cipher=FERNET.encrypt(secret.encode()).decode() if secret else None)
    with Session.begin() as db:db.add(sub);db.flush();id=sub.id
    return {'id':id,'source':source,'active':True,'webhook_secret':secret,'delivery':'at least once; deduplicate event_id; verify timestamp and HMAC'}

async def deliver():
    with Session() as db:ids=db.scalars(select(Delivery.id).where(Delivery.delivered==False,Delivery.attempts<6,Delivery.next_attempt<=now()).limit(20)).all()
    for id in ids:
        with Session.begin() as db:
            job=db.scalar(select(Delivery).where(Delivery.id==id).with_for_update(skip_locked=True))
            if not job or job.delivered:continue
            sub=db.get(Subscription,job.subscription_id);event=db.get(AlertEvent,job.event_id)
            if not sub.active:job.delivered=True;continue
            body=json.dumps({'event_id':event.id,'created_at':event.created_at.isoformat(),'data':event.payload},sort_keys=True).encode();stamp=str(int(now().timestamp()));secret=FERNET.decrypt(sub.secret_cipher.encode())
            signature=hmac.new(secret,stamp.encode()+b'.'+body,hashlib.sha256).hexdigest();job.attempts+=1;job.next_attempt=now()+timedelta(seconds=60*2**job.attempts)
            try:
                r=await fetch(sub.webhook,method='POST',data=body,headers={'Content-Type':'application/json','X-Omni-Timestamp':stamp,'X-Omni-Signature':'sha256='+signature,'X-Omni-Event-ID':event.id},limit=32_000,redirects=0)
                job.delivered=200<=r['status']<300
            except Exception:pass
