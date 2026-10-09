from datetime import datetime, timezone
import uuid
from sqlalchemy import create_engine, String, Text, JSON, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import DATABASE_URL

def now(): return datetime.now(timezone.utc)
def uid(): return str(uuid.uuid4())
engine=create_engine(DATABASE_URL, pool_pre_ping=True, **({'connect_args':{'check_same_thread':False}} if DATABASE_URL.startswith('sqlite') else {}))
Session=sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase): pass
class Account(Base):
    __tablename__='accounts'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    name:Mapped[str]=mapped_column(String(200))
    plan:Mapped[str]=mapped_column(String(20),default='free')
    stripe_customer:Mapped[str|None]=mapped_column(String(200),unique=True)
    subscription:Mapped[str|None]=mapped_column(String(200),unique=True)
class ApiKey(Base):
    __tablename__='api_keys'
    digest:Mapped[str]=mapped_column(String(64),primary_key=True)
    account_id:Mapped[str]=mapped_column(ForeignKey('accounts.id'),index=True)
    prefix:Mapped[str]=mapped_column(String(16))
    revoked:Mapped[bool]=mapped_column(Boolean,default=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Scan(Base):
    __tablename__='scans'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    owner:Mapped[str]=mapped_column(String(100),index=True)
    url:Mapped[str]=mapped_column(Text)
    public:Mapped[bool]=mapped_column(Boolean,default=False,index=True)
    status:Mapped[str]=mapped_column(String(20),default='queued',index=True)
    priority:Mapped[int]=mapped_column(Integer,default=0)
    attempts:Mapped[int]=mapped_column(Integer,default=0)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    started_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    report:Mapped[dict|None]=mapped_column(JSON)
    error:Mapped[str|None]=mapped_column(Text)
class BenchmarkRun(Base):
    __tablename__='benchmark_runs'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    owner:Mapped[str]=mapped_column(String(100),index=True)
    agent:Mapped[str]=mapped_column(String(200))
    agent_version:Mapped[str]=mapped_column(String(100))
    suite:Mapped[str]=mapped_column(String(40))
    seed:Mapped[int]=mapped_column(Integer)
    private:Mapped[bool]=mapped_column(Boolean,default=False)
    verified:Mapped[bool]=mapped_column(Boolean,default=False)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    result:Mapped[dict|None]=mapped_column(JSON)
    state:Mapped[dict]=mapped_column(JSON,default=dict)
class FeedSnapshot(Base):
    __tablename__='feed_snapshots'
    id:Mapped[str]=mapped_column(String(100),primary_key=True)
    fetched_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    payload:Mapped[dict]=mapped_column(JSON)
class Subscription(Base):
    __tablename__='alert_subscriptions'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    owner:Mapped[str]=mapped_column(String(100),index=True)
    source:Mapped[str]=mapped_column(String(100))
    webhook:Mapped[str|None]=mapped_column(Text)
    secret_cipher:Mapped[str|None]=mapped_column(Text)
    active:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class AlertEvent(Base):
    __tablename__='alert_events'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    source:Mapped[str]=mapped_column(String(100),index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    payload:Mapped[dict]=mapped_column(JSON)
class Delivery(Base):
    __tablename__='webhook_deliveries'
    __table_args__=(UniqueConstraint('event_id','subscription_id'),)
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    event_id:Mapped[str]=mapped_column(ForeignKey('alert_events.id'))
    subscription_id:Mapped[str]=mapped_column(ForeignKey('alert_subscriptions.id'))
    attempts:Mapped[int]=mapped_column(Integer,default=0)
    next_attempt:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    delivered:Mapped[bool]=mapped_column(Boolean,default=False)
class DirectoryEntry(Base):
    __tablename__='directory_entries'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    owner:Mapped[str]=mapped_column(String(100))
    name:Mapped[str]=mapped_column(String(200))
    url:Mapped[str]=mapped_column(Text)
    description:Mapped[str]=mapped_column(Text)
    approved:Mapped[bool]=mapped_column(Boolean,default=False)
    sponsored:Mapped[bool]=mapped_column(Boolean,default=False)
class BillingEvent(Base):
    __tablename__='billing_events'
    id:Mapped[str]=mapped_column(String(200),primary_key=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class AbuseReport(Base):
    __tablename__='abuse_reports'
    id:Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    url:Mapped[str]=mapped_column(Text)
    description:Mapped[str]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Certification(Base):
    __tablename__='certifications'
    domain:Mapped[str]=mapped_column(String(253),primary_key=True)
    account_id:Mapped[str]=mapped_column(ForeignKey('accounts.id'))
    scan_id:Mapped[str]=mapped_column(ForeignKey('scans.id'))
    expires_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    verified_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    verification_method:Mapped[str]=mapped_column(String(40))

def init_db(): Base.metadata.create_all(engine)

class PublicScore(Base):
    __tablename__='public_scores'
    domain:Mapped[str]=mapped_column(String(253),primary_key=True)
    payload:Mapped[dict]=mapped_column(JSON)
    html:Mapped[str]=mapped_column(Text)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class IndexNotification(Base):
    __tablename__='index_notifications'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    url:Mapped[str]=mapped_column(Text)
    attempts:Mapped[int]=mapped_column(Integer,default=0)
    next_attempt:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    accepted:Mapped[bool]=mapped_column(Boolean,default=False)
    last_status:Mapped[int|None]=mapped_column(Integer)
