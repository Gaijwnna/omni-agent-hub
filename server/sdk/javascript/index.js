export class OmniAgentHub {
  constructor(baseUrl,{apiKey}={}) {this.baseUrl=baseUrl.replace(/\/$/,'');this.apiKey=apiKey;}
  async request(path,{method='GET',body}={}) {
    const response=await fetch(this.baseUrl+path,{method,redirect:'error',signal:AbortSignal.timeout(30000),headers:{...(body?{'Content-Type':'application/json'}:{}),...(this.apiKey?{Authorization:`Bearer ${this.apiKey}`}:{})},body:body?JSON.stringify(body):undefined});
    if(!response.ok) throw Object.assign(new Error(`Omni API: HTTP ${response.status}`),{status:response.status,detail:await response.text()});
    return response.json();
  }
  scan(url,{public:publish=false}={}) {return this.request('/api/v1/scans',{method:'POST',body:{url,public:publish}});}
  report(id){return this.request(`/api/v1/scans/${encodeURIComponent(id)}`);}
  signals(){return this.request('/api/v1/signals');}
  startBenchmark(agent,agentVersion,{private:privateRun=false}={}) {return this.request('/api/v1/benchmark/runs',{method:'POST',body:{agent,agent_version:agentVersion,private:privateRun}});}
  finishBenchmark(id,answers){return this.request(`/api/v1/benchmark/runs/${encodeURIComponent(id)}/finish`,{method:'POST',body:{answers}});}
  format(content,{inputFormat='txt',outputFormat='json',encoding='utf8'}={}) {return this.request('/api/v1/format',{method:'POST',body:{content,input_format:inputFormat,output_format:outputFormat,encoding}});}
}
