import pytest,socket
from app.network import validate_url,public_ip,PublicResolver,FetchError
from app.scanner import analyse
HTML='<html><main><h1>Data</h1><label for="x">Email</label><input id="x"><table><tr><th>Value</th></tr><tr><td>12</td></tr></table></main></html>'
AUX={'llms':True,'api':True,'robots':{'OmniAgentScanner':True}}
@pytest.mark.parametrize('url',['http://127.0.0.1','http://localhost','http://[::1]','http://169.254.169.254','file:///etc/passwd','https://user:pass@example.com','https://example.com:22','http://[::ffff:127.0.0.1]'])
def test_reject_private(url):
    with pytest.raises(ValueError):validate_url(url)
@pytest.mark.asyncio
async def test_rebinding_resolver(monkeypatch):
    import asyncio
    async def fake(*args,**kwargs):return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',80)),(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',80))]
    monkeypatch.setattr(asyncio.get_running_loop(),'getaddrinfo',fake)
    with pytest.raises(FetchError):await PublicResolver().resolve('example.com',80)
def test_unknown_browser_does_not_receive_score():
    r=analyse(HTML,AUX);assert r['score'] is None;assert r['coverage']==70;assert r['score_range'][1]==100

def test_full_evidence_and_labels():
    r=analyse(HTML,AUX,{'cls':0,'text_characters':10});assert r['score']==100
    r=analyse(HTML.replace('<label for="x">Email</label>',''),AUX,{'cls':.3,'text_characters':100});assert r['score']<80

def test_captcha():
    r=analyse(HTML+'<div class="g-recaptcha"></div>',AUX)
    assert next(c for c in r['checks'] if c['id']=='captcha')['earned']==0
