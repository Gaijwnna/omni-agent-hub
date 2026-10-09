import hashlib,hmac,secrets,time,asyncio
from contextvars import ContextVar
from dataclasses import dataclass
from fastapi import HTTPException
from sqlalchemy import select
from redis.asyncio import Redis
from .config import SECRET,REDIS_URL,PRODUCTION
from .db import Session,ApiKey,Account

@dataclass
class Identity:
    id:str
    plan:str='free'
    account:bool=False
    rate_subject:str='anonymous'
identity=ContextVar('identity',default=Identity('anonymous'))
def digest(value):return hmac.new(SECRET.encode(),value.encode(),hashlib.sha256).hexdigest()

def authenticate(key,ip):
    if key:
        with Session() as db:
            item=db.get(ApiKey,digest(key))
            if not item or item.revoked:raise HTTPException(401,'Invalid API key')
            account=db.get(Account,item.account_id)
            return Identity(account.id,account.plan,True,'ip:'+digest(ip))
    return Identity('ip:'+digest(ip),rate_subject='ip:'+digest(ip))
def require_account():
    who=identity.get()
    if not who.account:raise HTTPException(401,'An API key is required for durable private resources')
    return who

def mint_key(account_id):
    raw='oah_'+secrets.token_urlsafe(32)
    with Session.begin() as db:db.add(ApiKey(digest=digest(raw),account_id=account_id,prefix=raw[:12]))
    return raw

redis=Redis.from_url(REDIS_URL) if REDIS_URL else None
local={};lock=asyncio.Lock()
LIMITS={'free':{'read':60,'scan':5,'write':10},'pro':{'read':600,'scan':100,'write':100},'team':{'read':1800,'scan':500,'write':300}}
async def rate_limit(bucket,cost=1):
    who=identity.get();limit=LIMITS.get(who.plan,LIMITS['free'])[bucket];window=3600 if bucket=='scan' else 60
    subject=who.id if who.account else who.rate_subject
    key=f'limit:{subject}:{bucket}:{int(time.time())//window}'
    if redis:
        try:
            n=await redis.eval("local n=redis.call('INCRBY',KEYS[1],ARGV[1]);if n==tonumber(ARGV[1]) then redis.call('EXPIRE',KEYS[1],ARGV[2]) end;return n",1,key,cost,window+1)
        except Exception:raise HTTPException(503,'Rate limiter unavailable')
    else:
        if PRODUCTION:raise HTTPException(503,'Rate limiter unavailable')
        async with lock:
            t=time.time()
            for k in list(local):
                if local[k][1]<t:del local[k]
            n=local.get(key,(0,0))[0]+cost;local[key]=(n,t+window)
    if n>limit:raise HTTPException(429,'Rate limit reached',headers={'Retry-After':str(window-int(time.time())%window)})

def owned(row,allow_public=False):
    if not row or (row.owner!=identity.get().id and not (allow_public and getattr(row,'public',False))):raise HTTPException(404,'Not found')
    return row
