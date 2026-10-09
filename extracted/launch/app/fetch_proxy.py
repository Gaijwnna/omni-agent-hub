"""Internal-only GET broker. The browser container has no direct internet network."""
import asyncio,base64
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from .network import validate_url,fetch_once,robots,USER_AGENT
app=FastAPI(docs_url=None,openapi_url=None)
limit=asyncio.Semaphore(12)
class Request(BaseModel):url:str
@app.post('/fetch')
async def get_public(data:Request):
    async with limit:
        try:
            url=validate_url(data.url);policy,_=await robots(url)
            if not policy.can_fetch(USER_AGENT,url):raise ValueError('Robots policy forbids this URL')
            result=await fetch_once(url)
            return {'status':result['status'],'headers':result['headers'],'body':base64.b64encode(result['body']).decode()}
        except Exception:raise HTTPException(422,'Public resource fetch rejected or unavailable')
