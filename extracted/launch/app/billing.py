"""Configured integrations only: no simulated payment success or token-hash verification."""
import os,asyncio
from fastapi import HTTPException
from sqlalchemy import select
from .db import Session,Account,BillingEvent
from .security import require_account
from .config import PUBLIC_URL

async def checkout(plan):
    who=require_account();price=os.getenv('STRIPE_PRICE_'+plan.upper(),'');secret=os.getenv('STRIPE_SECRET_KEY','')
    if plan not in ('pro','team') or not price or not secret:raise HTTPException(503,'Subscription checkout is not configured')
    import stripe
    stripe.api_key=secret
    with Session() as db:account=db.get(Account,who.id);customer=account.stripe_customer
    if not customer:
        result=await asyncio.to_thread(stripe.Customer.create,metadata={'account_id':who.id},idempotency_key='customer:'+who.id)
        customer=result.id
        with Session.begin() as db:db.get(Account,who.id).stripe_customer=customer
    result=await asyncio.to_thread(stripe.checkout.Session.create,mode='subscription',customer=customer,line_items=[{'price':price,'quantity':1}],client_reference_id=who.id,subscription_data={'metadata':{'account_id':who.id}},success_url=PUBLIC_URL+'/pricing?checkout=complete',cancel_url=PUBLIC_URL+'/pricing')
    return {'checkout_url':result.url,'note':'Entitlements change only after a verified Stripe webhook, not this redirect.'}
async def webhook(raw,signature):
    import stripe
    secret=os.getenv('STRIPE_WEBHOOK_SECRET','')
    if not secret:raise HTTPException(503,'Stripe webhook is not configured')
    try:event=stripe.Webhook.construct_event(raw,signature,secret)
    except Exception:raise HTTPException(400,'Invalid webhook signature')
    with Session() as db:
        if db.get(BillingEvent,event.id):return {'received':True}
    if event.type in ('customer.subscription.created','customer.subscription.updated','customer.subscription.deleted'):
        stripe.api_key=os.getenv('STRIPE_SECRET_KEY','')
        # Read the latest object to avoid out-of-order webhook projection errors.
        subscription=await asyncio.to_thread(stripe.Subscription.retrieve,event.data.object.id)
        price=subscription['items']['data'][0]['price']['id'] if subscription['items']['data'] else ''
        plan=next((p for p in ('pro','team') if os.getenv('STRIPE_PRICE_'+p.upper())==price),'free')
        if subscription.status not in ('active','trialing'):plan='free'
        with Session.begin() as db:
            account=db.scalar(select(Account).where(Account.stripe_customer==subscription.customer).with_for_update())
            if not account:raise HTTPException(409,'Unknown billing customer')
            account.plan=plan;account.subscription=subscription.id
    from sqlalchemy.exc import IntegrityError
    try:
        with Session.begin() as db:db.add(BillingEvent(id=event.id))
    except IntegrityError:pass
    return {'received':True}

def install_x402(app):
    if os.getenv('X402_ENABLED')!='1':return False
    wallet=os.getenv('X402_PAY_TO','');facilitator=os.getenv('X402_FACILITATOR_URL','');network=os.getenv('X402_NETWORK','eip155:84532')
    if not wallet or not facilitator:raise RuntimeError('x402 requires a real wallet and a compatible facilitator')
    from x402.http import FacilitatorConfig,HTTPFacilitatorClient,PaymentOption
    from x402.http.middleware.fastapi import PaymentMiddlewareASGI
    from x402.http.types import RouteConfig
    from x402.mechanisms.evm.exact import ExactEvmServerScheme
    from x402.server import x402ResourceServer
    server=x402ResourceServer(HTTPFacilitatorClient(FacilitatorConfig(url=facilitator)))
    server.register(network,ExactEvmServerScheme())
    routes={path:RouteConfig(accepts=[PaymentOption(scheme='exact',pay_to=wallet,price=price,network=network)],mime_type='application/json',description=description) for path,price,description in [
        ('POST /api/v1/paid/scans/bulk',os.getenv('X402_BULK_PRICE','$0.10'),'Up to 20 readiness scans'),
        ('POST /api/v1/paid/scans/priority',os.getenv('X402_SCAN_PRICE','$0.01'),'Priority readiness scan')
    ]}
    app.add_middleware(PaymentMiddlewareASGI,routes=routes,server=server)
    return True
