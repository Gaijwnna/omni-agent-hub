import time
import httpx
class OmniAgentHub:
    def __init__(self,base_url,api_key=None):
        self.http=httpx.Client(base_url=base_url.rstrip('/'),headers={'Authorization':'Bearer '+api_key} if api_key else {},timeout=30,follow_redirects=False)
    def request(self,method,path,**kwargs):
        response=self.http.request(method,path,**kwargs);response.raise_for_status();return response.json()
    def scan(self,url,public=False):return self.request('POST','/api/v1/scans',json={'url':url,'public':public})
    def report(self,scan_id):return self.request('GET','/api/v1/scans/'+scan_id)
    def wait_for_scan(self,scan_id,timeout=90):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            r=self.report(scan_id)
            if r['status'] in ('completed','failed'):return r
            time.sleep(3)
        raise TimeoutError('Scan is still pending')
    def signals(self):return self.request('GET','/api/v1/signals')
    def start_benchmark(self,agent,version,private=False):return self.request('POST','/api/v1/benchmark/runs',json={'agent':agent,'agent_version':version,'private':private})
    def finish_benchmark(self,run_id,answers):return self.request('POST',f'/api/v1/benchmark/runs/{run_id}/finish',json={'answers':answers})
    def format(self,content,input_format='txt',output_format='json',encoding='utf8'):return self.request('POST','/api/v1/format',json={'content':content,'input_format':input_format,'output_format':output_format,'encoding':encoding})
    def close(self):self.http.close()
