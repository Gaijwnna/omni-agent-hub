"""Local administrator commands. Never expose these through public MCP or REST."""
import argparse,base64,secrets,json
from .db import Session,init_db,Account,DirectoryEntry
from .security import mint_key

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['generate-secrets','create-account','approve-directory']);p.add_argument('--name');p.add_argument('--id');p.add_argument('--sponsored',action='store_true');args=p.parse_args()
    if args.command=='generate-secrets':
        print('Generate these on the deployment host; do not share or commit the output.')
        print('APP_SECRET='+secrets.token_urlsafe(48));print('POSTGRES_PASSWORD='+secrets.token_urlsafe(32));print('BENCHMARK_SIGNING_KEY='+base64.b64encode(secrets.token_bytes(32)).decode());return
    init_db()
    if args.command=='create-account':
        if not args.name:p.error('--name is required')
        with Session.begin() as db:a=Account(name=args.name);db.add(a);db.flush();id=a.id
        print(json.dumps({'account_id':id,'api_key':mint_key(id)}))
    if args.command=='approve-directory':
        with Session.begin() as db:
            item=db.get(DirectoryEntry,args.id)
            if not item:p.error('Entry not found')
            item.approved=True;item.sponsored=args.sponsored
        print('Directory entry approved; sponsored flag set explicitly.')
if __name__=='__main__':main()
