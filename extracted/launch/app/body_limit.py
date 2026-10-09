from starlette.responses import JSONResponse
class BodyLimitMiddleware:
    def __init__(self,app,limit=7_100_000):self.app,self.limit=app,limit
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope['method'] not in ('POST','PUT','PATCH'):
            return await self.app(scope,receive,send)
        body=bytearray()
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            body.extend(message.get('body',b''))
            if len(body)>self.limit:return await JSONResponse({'detail':'Request too large'},413)(scope,receive,send)
            if not message.get('more_body'):break
        consumed=False
        async def bounded_receive():
            nonlocal consumed
            if not consumed:consumed=True;return {'type':'http.request','body':bytes(body),'more_body':False}
            return await receive()
        await self.app(scope,bounded_receive,send)
