import asyncio,logging
from datetime import timedelta
from sqlalchemy import select,delete
from .db import Session,Scan,AbuseReport,AlertEvent,now,init_db
from .scanner import scan
from .discovery import publish_scan,notify_indexnow,queue_reference_pages
from .feeds import refresh,deliver
log=logging.getLogger('omni.worker')
async def process_scan():
    with Session.begin() as db:
        stale=db.scalars(select(Scan).where(Scan.status=='running',Scan.started_at<now()-timedelta(minutes=3))).all()
        for item in stale:item.status='queued' if item.attempts<3 else 'failed';item.error='Worker interrupted; retry limit reached' if item.attempts>=3 else None
        row=db.scalar(select(Scan).where(Scan.status=='queued').order_by(Scan.priority.desc(),Scan.created_at).with_for_update(skip_locked=True).limit(1))
        if not row:return False
        row.status='running';row.started_at=now();row.attempts+=1;id,url=row.id,row.url
    try:report=await scan(url);error=None
    except Exception as e:report=None;error=str(e)[:300] or type(e).__name__
    with Session.begin() as db:
        row=db.get(Scan,id)
        if row:
            row.status='completed' if report else 'failed';row.report=report;row.error=error
            db.flush();publish_scan(db,row)
    return True
async def main():
    init_db();queue_reference_pages();next_feed=0;next_clean=0
    while True:
        if asyncio.get_running_loop().time()>=next_feed:
            try:await refresh()
            except Exception:log.warning('Public data refresh failed; previous snapshot retained')
            next_feed=asyncio.get_running_loop().time()+900
        try:
            worked=await process_scan();await deliver();await notify_indexnow()
            if asyncio.get_running_loop().time()>=next_clean:
                with Session.begin() as db:
                    db.execute(delete(Scan).where(Scan.public==False,Scan.created_at<now()-timedelta(days=30)))
                    db.execute(delete(AbuseReport).where(AbuseReport.created_at<now()-timedelta(days=90)))
                next_clean=asyncio.get_running_loop().time()+3600
        except Exception:log.exception('Worker task failed');worked=False
        if not worked:await asyncio.sleep(2)
if __name__=='__main__':asyncio.run(main())
