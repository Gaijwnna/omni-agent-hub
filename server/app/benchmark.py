import os,json,hashlib,base64,secrets
from datetime import date,timedelta
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from .db import BenchmarkRun,Session,now
from .security import identity,owned,require_account
from fastapi import HTTPException

SUITE='2026-10.v1'
CHALLENGES=['nested_menu','matrix','multi_step','shifting_state','iframe','date_picker','file_upload']
def spec(seed):
    # Deterministic fixtures. A signature proves this service assessed answers, not who operated the browser.
    n=seed%4+1
    return {'suite':SUITE,'seed':seed,'challenges':[
      {'id':'nested_menu','instruction':f'Select Europe / United Kingdom / London / Zone {n}.'},
      {'id':'matrix','instruction':'Enable A1, B2, C3 and D4 only.'},
      {'id':'multi_step','instruction':f'Complete the two steps for Project {seed} with delivery Email.'},
      {'id':'shifting_state','instruction':f'Read revision {n}, then submit its visible value.'},
      {'id':'iframe','instruction':f'Enter frame code FRAME-{seed}.'},
      {'id':'date_picker','instruction':f'Select {(date(2026,10,1)+timedelta(days=seed%28)).isoformat()}.'},
      {'id':'file_upload','instruction':f'Upload a UTF-8 text file containing OMNI-{seed}.'}]}
def expected(seed):
    return {'nested_menu':f'Europe/United Kingdom/London/Zone {seed%4+1}','matrix':['A1','B2','C3','D4'],'multi_step':{'project':f'Project {seed}','delivery':'Email'},'shifting_state':{'revision':seed%4+1,'value':f'STATE-{seed}'},'iframe':f'FRAME-{seed}','date_picker':(date(2026,10,1)+timedelta(days=seed%28)).isoformat(),'file_upload':hashlib.sha256(f'OMNI-{seed}'.encode()).hexdigest()}
def key():
    raw=os.getenv('BENCHMARK_SIGNING_KEY','')
    if not raw:raise HTTPException(503,'Benchmark signing key is not configured')
    return Ed25519PrivateKey.from_private_bytes(base64.b64decode(raw,validate=True))
def public_key():
    return {'algorithm':'Ed25519','key_id':os.getenv('SIGNING_KEY_ID','benchmark-1'),'public_key':base64.b64encode(key().public_key().public_bytes_raw()).decode()}
def start(agent,agent_version,private=False):
    who=identity.get()
    if private and (not who.account or who.plan not in ('pro','team')):raise HTTPException(403,'Private runs require Pro or Team')
    key() # Do not create unsigned runs.
    run=BenchmarkRun(owner=who.id,agent=agent,agent_version=agent_version,suite=SUITE,seed=secrets.randbelow(1_000_000),private=private,state={})
    with Session.begin() as db:db.add(run);db.flush();result={'id':run.id,'suite':SUITE,'seed':run.seed,'challenge_url':f'/benchmark/runs/{run.id}','specification':spec(run.seed),'assurance':'community_unverified'}
    return result

def get(run_id):
    with Session() as db:
        run=owned(db.get(BenchmarkRun,run_id))
        return {'id':run.id,'agent':run.agent,'agent_version':run.agent_version,'suite':run.suite,'seed':run.seed,'private':run.private,'verified':run.verified,'result':run.result,'state':run.state,'specification':spec(run.seed)}
def finish(run_id,answers):
    with Session.begin() as db:
        run=db.scalar(__import__('sqlalchemy').select(BenchmarkRun).where(BenchmarkRun.id==run_id).with_for_update());owned(run)
        if run.result:return run.result
        truth=expected(run.seed);checks={k:answers.get(k)==v for k,v in truth.items()}
        result={'run_id':run.id,'agent':run.agent,'agent_version':run.agent_version,'suite':run.suite,'seed':run.seed,'suite_sha256':hashlib.sha256(json.dumps(spec(run.seed),sort_keys=True).encode()).hexdigest(),'score':round(100*sum(checks.values())/len(checks),2),'checks':checks,'completed_at':now().isoformat(),'assurance':'community_unverified','ranked':False}
        canonical=json.dumps(result,sort_keys=True,separators=(',',':')).encode();result['signature']=base64.b64encode(key().sign(canonical)).decode();result['key_id']=public_key()['key_id'];run.result=result
        return result

def leaderboard():
    from sqlalchemy import select
    with Session() as db:
        rows=db.scalars(select(BenchmarkRun).where(BenchmarkRun.verified==True,BenchmarkRun.private==False,BenchmarkRun.suite==SUITE)).all()
        items=[{'id':r.id,'agent':r.agent,'version':r.agent_version,'suite':r.suite,'score':r.result['score'],'assurance':'operator_verified'} for r in rows if r.result]
    return {'suite':SUITE,'items':sorted(items,key=lambda r:(-r['score'],r['agent'])),'policy':'Only independently witnessed runs are ranked. Community runs remain unranked. No invented seed rankings.'}
