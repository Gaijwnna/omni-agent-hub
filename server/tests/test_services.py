import base64,json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from app.db import Session,Scan,FeedSnapshot
from app.scanner import analyse
from app.benchmark import expected
from app.feeds import SOURCE

def test_initial_html_and_discovery(client):
    for path in ['/','/signals','/benchmark','/tools/claims','/tools/formatter','/status','/docs/privacy','/docs/terms','/docs/cookies','/docs/acceptable-use']:
        r=client.get(path);assert r.status_code==200;assert '<h1>' in r.text;assert 'application/ld+json' in r.text
    assert client.get('/openapi.json').json()['paths']['/api/v1/scans']
    assert client.get('/.well-known/agent.json').json()['interfaces']['mcp']['url'].endswith('/mcp')

def test_signal_html_json_parity(client):
    row={'id':'fixture','description':'Fixture area','severity':'Fixture warning','source_url':'https://example.com/fixture','licence':'https://example.com/licence','updated_at':'2026-10-08T00:00:00Z'}
    with Session.begin() as db:db.merge(FeedSnapshot(id=SOURCE,payload={'items':[row],'status':'available','source_url':'https://example.com','licence':'https://example.com'}))
    api=client.get('/api/v1/signals').json();html=client.get('/signals').text
    for key in ['description','severity','updated_at','source_url','licence']:assert api['items'][0][key] in html

def test_private_scan_and_rate_limits(client):
    key=client.post('/api/v1/keys',json={'name':'Tester'}).json()['api_key'];headers={'Authorization':'Bearer '+key}
    r=client.post('/api/v1/scans',json={'url':'https://example.com'},headers=headers);assert r.status_code==202
    id=r.json()['id'];assert client.get('/api/v1/scans/'+id).status_code==404
    assert client.get('/api/v1/scans/'+id,headers=headers).status_code==200
    for i in range(4):assert client.post('/api/v1/scans',json={'url':'https://example.com'},headers=headers).status_code==202
    assert client.post('/api/v1/scans',json={'url':'https://example.com'},headers=headers).status_code==429
    assert client.get('/api/v1/signals',headers={'Authorization':'Bearer invalid'}).status_code==401

def test_public_scan_report_and_badge(client):
    r=client.post('/api/v1/scans',json={'url':'https://example.com','public':True});id=r.json()['id']
    report=analyse('<main><h1>Test</h1></main>',{'llms':True,'api':True,'robots':{'Omni':True}},{'cls':0,'text_characters':4});report.update(scanned_at='2026-10-08',browser_error=None)
    with Session.begin() as db:row=db.get(Scan,id);row.report=report;row.status='completed'
    assert client.get('/badges/'+id+'.svg').status_code==200
    assert '100' in client.get('/scans/'+id).text

def test_signed_benchmark_and_no_fake_rankings(client):
    r=client.post('/api/v1/benchmark/runs',json={'agent':'Fixture agent','agent_version':'test'});assert r.status_code==201
    run=r.json();result=client.post('/api/v1/benchmark/runs/'+run['id']+'/finish',json={'answers':expected(run['seed'])}).json();assert result['score']==100
    pub=client.get('/.well-known/benchmark-key.json').json()['public_key'];signature=base64.b64decode(result.pop('signature'));result.pop('key_id')
    Ed25519PublicKey.from_public_bytes(base64.b64decode(pub)).verify(signature,json.dumps(result,sort_keys=True,separators=(',',':')).encode())
    assert client.get('/api/v1/leaderboard').json()['items']==[]

def test_mcp_round_trip(client):
    headers={'Accept':'application/json, text/event-stream','Content-Type':'application/json'}
    init=client.post('/mcp',headers=headers,json={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'test','version':'1'}}})
    assert init.status_code==200,init.text
    r=client.post('/mcp',headers=headers,json={'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}});assert r.status_code==200,r.text
    names=[t['name'] for t in r.json()['result']['tools']];assert 'scan_site' in names and 'format_payload' in names
    r=client.post('/mcp',headers=headers,json={'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'list_signals','arguments':{}}})
    result=r.json()['result'];assert not result.get('isError');assert result['structuredContent']==client.get('/api/v1/signals').json()

def test_payments_fail_closed(client):
    assert client.post('/api/v1/paid/scans/bulk',json={'urls':['https://example.com']}).status_code==503
    assert client.post('/api/v1/billing/stripe-webhook',content='{}').status_code==503

def test_mcp_ownership_is_shared_with_rest(client):
    key=client.post('/api/v1/keys',json={'name':'MCP identity fixture'}).json()['api_key']
    headers={'Accept':'application/json, text/event-stream','Content-Type':'application/json','Authorization':'Bearer '+key}
    r=client.post('/mcp',headers=headers,json={'jsonrpc':'2.0','id':7,'method':'tools/call','params':{'name':'scan_site','arguments':{'url':'https://example.com'}}})
    result=r.json()['result'];assert not result.get('isError'),result
    id=result['structuredContent']['id']
    assert client.get('/api/v1/scans/'+id,headers={'Authorization':'Bearer '+key}).status_code==200
    assert client.get('/api/v1/scans/'+id).status_code==404
