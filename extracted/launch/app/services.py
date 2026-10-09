import asyncio,base64
from typing import Literal
from urllib.parse import urlsplit
from pydantic import BaseModel,Field,ConfigDict
from sqlalchemy import select
from fastapi import HTTPException
from .db import Session,Scan,DirectoryEntry,AbuseReport,AlertEvent,Subscription,now
from .security import identity,rate_limit,owned,require_account
from .network import validate_url
from . import benchmark,feeds
from .claims import Claim,draft
from .formatter import convert_isolated,MAX_UPLOAD

class Input(BaseModel):model_config=ConfigDict(extra='forbid')
class ScanInput(Input):
    url:str=Field(min_length=8,max_length=2048)
    public:bool=False
class BulkInput(Input):urls:list[str]=Field(min_length=1,max_length=20)
class RunInput(Input):
    agent:str=Field(min_length=1,max_length=200)
    agent_version:str=Field(min_length=1,max_length=100)
    private:bool=False
class FinishInput(Input):answers:dict
class FormatInput(Input):
    content:str=Field(max_length=7_000_000)
    input_format:Literal['txt','html','json','markdown','pdf']='txt'
    output_format:Literal['json','markdown','llms']='json'
    encoding:Literal['utf8','base64']='utf8'
class SubscribeInput(Input):
    source:Literal['ea-flood-warnings']='ea-flood-warnings'
    webhook:str|None=None
class SubmitAgent(Input):
    name:str=Field(min_length=1,max_length=200)
    url:str=Field(min_length=8,max_length=2048)
    description:str=Field(min_length=10,max_length=2000)
class AbuseInput(Input):
    url:str=Field(min_length=1,max_length=2048)
    description:str=Field(min_length=10,max_length=5000)

async def create_scan(data:ScanInput,priority=0,premium=False):
    if not premium:await rate_limit('scan')
    url=validate_url(data.url)
    if urlsplit(url).query:raise ValueError('Remove query parameters; scan public URLs without tokens or personal information')
    with Session.begin() as db:
        row=Scan(owner=identity.get().id,url=url,public=data.public,priority=priority);db.add(row);db.flush();id=row.id
    return {'id':id,'status':'queued','public':data.public,'report_url':f'/scans/{id}','api_url':f'/api/v1/scans/{id}'}
async def get_scan(id):
    with Session() as db:
        row=owned(db.get(Scan,id),True)
        return {'id':row.id,'url':row.url,'status':row.status,'public':row.public,'report':row.report,'error':row.error,'created_at':row.created_at.isoformat()}
async def format_payload(data:FormatInput):
    await rate_limit('write')
    raw=base64.b64decode(data.content,validate=True) if data.encoding=='base64' else data.content.encode()
    if data.input_format=='pdf' and data.encoding!='base64':raise ValueError('PDF requests require base64 encoding')
    if len(raw)>MAX_UPLOAD:raise ValueError('File exceeds 5 MB')
    return await asyncio.to_thread(convert_isolated,raw,data.input_format,data.output_format)
async def create_claim(data:Claim):
    await rate_limit('write');return draft(data)
async def start_run(data:RunInput):
    await rate_limit('write');return benchmark.start(data.agent,data.agent_version,data.private)
async def finish_run(id,data:FinishInput):
    await rate_limit('write');return benchmark.finish(id,data.answers)
async def subscribe(data:SubscribeInput):
    await rate_limit('write');return feeds.subscribe(data.source,data.webhook)
async def events(subscription_id):
    with Session() as db:
        sub=owned(db.get(Subscription,subscription_id));rows=db.scalars(select(AlertEvent).where(AlertEvent.source==sub.source,AlertEvent.created_at>=sub.created_at).order_by(AlertEvent.created_at.desc()).limit(100)).all()
        return {'subscription_id':sub.id,'active':sub.active,'events':[{'id':r.id,'created_at':r.created_at.isoformat(),'data':r.payload} for r in rows]}
async def unsubscribe(subscription_id):
    with Session.begin() as db:sub=owned(db.get(Subscription,subscription_id));sub.active=False
    return {'id':subscription_id,'active':False}
async def submit_agent(data:SubmitAgent):
    await rate_limit('write');validate_url(data.url)
    with Session.begin() as db:
        row=DirectoryEntry(owner=identity.get().id,**data.model_dump(),approved=False,sponsored=False);db.add(row);db.flush();id=row.id
    return {'id':id,'status':'pending_review','sponsored':False}
async def directory():
    with Session() as db:
        return {'items':[{'id':x.id,'name':x.name,'url':x.url,'description':x.description,'sponsored':x.sponsored} for x in db.scalars(select(DirectoryEntry).where(DirectoryEntry.approved==True).order_by(DirectoryEntry.name))]}
async def report_abuse(data:AbuseInput):
    await rate_limit('write')
    with Session.begin() as db:row=AbuseReport(**data.model_dump());db.add(row);db.flush();id=row.id
    return {'id':id,'status':'received'}
