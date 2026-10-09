from datetime import date
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict

SOURCES=['https://www.caa.co.uk/air-passengers/travel-problems-and-rights/flight-delays-and-cancellations/delays/','https://europa.eu/youreurope/citizens/travel/passenger-rights/air/index_en.htm']
class Claim(BaseModel):
    model_config=ConfigDict(extra='forbid')
    passenger:str=Field(min_length=1,max_length=200)
    address:str=Field(min_length=1,max_length=1000)
    email:str=Field(min_length=3,max_length=254)
    airline:str=Field(min_length=1,max_length=200)
    airline_address:str=Field(min_length=1,max_length=1000)
    flight_number:str=Field(min_length=2,max_length=20)
    flight_date:date
    booking_reference:str=Field(min_length=1,max_length=30)
    departure:str=Field(min_length=1,max_length=100)
    arrival:str=Field(min_length=1,max_length=100)
    distance_km:int=Field(gt=0,le=22000)
    arrival_delay_minutes:int=Field(ge=0,le=10080)
    regime:Literal['UK261','EU261']
    departure_jurisdiction:Literal['UK','EU','other']
    arrival_jurisdiction:Literal['UK','EU','other']
    operating_carrier:Literal['UK','EU','other']
    extraordinary_circumstances:Literal['no','yes','unknown']='unknown'
    details:str=Field(min_length=1,max_length=5000)

def draft(c:Claim):
    if c.flight_date>date.today():raise ValueError('Flight date cannot be in the future')
    applies=(c.departure_jurisdiction=='UK' or (c.arrival_jurisdiction=='UK' and c.operating_carrier in ('UK','EU')) or (c.arrival_jurisdiction=='EU' and c.operating_carrier=='UK')) if c.regime=='UK261' else (c.departure_jurisdiction=='EU' or (c.arrival_jurisdiction=='EU' and c.operating_carrier=='EU'))
    intra_eu=c.departure_jurisdiction==c.arrival_jurisdiction=='EU'
    band=0 if c.distance_km<=1500 else 1 if c.distance_km<=3500 or (c.regime=='EU261' and intra_eu) else 2
    amount=([220,350,520] if c.regime=='UK261' else [250,400,600])[band]
    if band==2 and c.arrival_delay_minutes<240:amount//=2
    eligible=applies and c.arrival_delay_minutes>=180 and c.extraordinary_circumstances=='no'
    currency='GBP' if c.regime=='UK261' else 'EUR'
    request=f'I request compensation of {currency} {amount} under {c.regime}, subject to confirmation of eligibility.' if eligible else 'Please explain the cause of the disruption, confirm the applicable passenger-rights rules, and assess my eligibility for compensation.'
    letter=f'''{c.passenger}\n{c.address}\n{c.email}\n\n{date.today().isoformat()}\n\nCustomer Relations\n{c.airline}\n{c.airline_address}\n\nSubject: Arrival delay — flight {c.flight_number}, {c.flight_date}, booking {c.booking_reference}\n\nDear Customer Relations Team,\n\nI travelled from {c.departure} to {c.arrival} on the above flight. My arrival at the final destination was delayed by {c.arrival_delay_minutes} minutes. The flight distance entered for this claim is {c.distance_km} km.\n\n{c.details}\n\n{request}\n\nPlease provide a written response and any evidence supporting a decision to decline compensation. I can supply my booking confirmation, boarding pass and supporting records on request.\n\nYours faithfully,\n{c.passenger}\n'''
    return {'letter':letter,'regime':c.regime,'potential_compensation':{'amount':amount if eligible else None,'currency':currency,'per_passenger':True},'assessment':'potentially_eligible' if eligible else 'requires_review','rules_version':'delay-2026-10-08','sources':SOURCES,'disclaimer':'Not legal advice. This draft uses your supplied facts for a single direct flight delay, not cancellation, denied boarding or complex connections. Verify distance, jurisdiction and extraordinary circumstances. You submit it yourself. No claim or personal details are stored.'}
