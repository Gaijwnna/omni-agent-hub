"""Separate container: no DB, account, billing or signing secrets."""
import asyncio,os,base64
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright
from .network import validate_url, fetch_once, robots, USER_AGENT
app=FastAPI(docs_url=None,openapi_url=None)
semaphore=asyncio.Semaphore(2)
class Target(BaseModel):url:str
@app.post('/render')
async def render(target:Target):
    url=validate_url(target.url)
    async with semaphore, asyncio.timeout(35), async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,chromium_sandbox=True)
        try:
            context=await browser.new_context(viewport={'width':1365,'height':768},user_agent=USER_AGENT,service_workers='block',accept_downloads=False)
            requests=0;blocked=0;robots_cache={}
            async def route(handler):
                nonlocal requests,blocked
                requests+=1
                if requests>100 or handler.request.method!='GET':blocked+=1;await handler.abort();return
                try:
                    target_url=validate_url(handler.request.url)
                    async with httpx.AsyncClient(timeout=18,trust_env=False) as client:
                        response=await client.post(os.getenv('FETCH_PROXY_URL','http://fetch-proxy:8002')+'/fetch',json={'url':target_url});response.raise_for_status();r=response.json();r['body']=base64.b64decode(r['body'],validate=True)
                    headers={k:v for k,v in r['headers'].items() if k.lower() not in ('content-encoding','content-length','transfer-encoding','set-cookie')}
                    await handler.fulfill(status=r['status'],headers=headers,body=r['body'])
                except Exception:blocked+=1;await handler.abort()
            await context.route('**/*',route)
            await context.route_web_socket('**/*',lambda ws:ws.close())
            page=await context.new_page()
            await page.add_init_script("""window.__shifts=[];new PerformanceObserver(list=>{for(const e of list.getEntries())if(!e.hadRecentInput)window.__shifts.push({v:e.value,t:e.startTime})}).observe({type:'layout-shift',buffered:true});""")
            await page.goto(url,wait_until='domcontentloaded',timeout=20000)
            await page.wait_for_timeout(5000)
            observed=await page.evaluate("""()=>{let max=0,sum=0,start=0,last=0;for(const e of window.__shifts||[]){if(e.t-last>1000||e.t-start>5000){sum=0;start=e.t}sum+=e.v;max=Math.max(max,sum);last=e.t}return {cls:max,text_characters:(document.body?.innerText||'').length,captcha:!!document.querySelector('[class*=recaptcha],[class*=h-captcha],[class*=cf-turnstile],iframe[src*=recaptcha]')}}""")
            return {**observed,'viewport':{'width':1365,'height':768},'browser_version':browser.version,'requests':requests,'blocked_requests':blocked,'observation_seconds':5}
        finally:await browser.close()
