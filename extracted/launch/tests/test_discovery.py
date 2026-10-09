from sqlalchemy import select
from app.db import Session,Scan,IndexNotification,PublicScore
from app.discovery import publish_scan,public_score,notify_indexnow,BOTS
import pytest

def report(score,stamp):
    return {'score':score,'coverage':100 if score is not None else 70,'score_range':[70,100],'scanned_at':stamp,'methodology_version':'readiness-test','checks':[],'limitations':['Fixture only'],'browser_error':None}

def test_materialized_public_history_and_interfaces(client):
    with Session.begin() as db:
        a=Scan(owner='a',url='https://history.example/a',public=True,status='completed',report=report(87,'2026-10-01T00:00:00Z'));db.add(a);db.flush();publish_scan(db,a)
        b=Scan(owner='b',url='https://history.example/b',public=True,status='completed',report=report(None,'2026-10-08T00:00:00Z'));db.add(b);db.flush();publish_scan(db,b)
        c=Scan(owner='a',url='https://secret.example/private',public=False,status='completed',report=report(99,'2026-10-08T00:00:00Z'));db.add(c);db.flush();publish_scan(db,c)
    page=client.get('/score/history.example')
    assert page.status_code==200 and 'measurement coverage is 70%' in page.text
    assert '87' in page.text and 'score-history' in page.text and 'rel="canonical"' in page.text
    assert client.get('/api/v1/scores/history.example').json()==public_score('history.example')
    assert client.get('/score/secret.example').status_code==404
    xml=client.get('/sitemap.xml').text
    assert '/score/history.example' in xml and 'secret.example' not in xml and '/scans/' not in xml
    with Session() as db:assert len(db.scalars(select(IndexNotification)).all())==2

def test_robots_and_reference_pages(client):
    text=client.get('/robots.txt').text
    for bot in BOTS:assert 'User-agent: '+bot+'\n' in text
    assert 'Sitemap:' in text
    for path in ('/datasets/ea-flood-warnings','/claims/uk261','/claims/eu261','/routes/get-api-v1-signals'):
        response=client.get(path);assert response.status_code==200
        assert 'direct-answer' in response.text and '<table' in response.text and 'Source:' in response.text

@pytest.mark.asyncio
async def test_indexnow_disabled_without_key(monkeypatch):
    monkeypatch.delenv('INDEXNOW_KEY',raising=False)
    await notify_indexnow()
