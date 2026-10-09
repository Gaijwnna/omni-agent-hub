import pytest
from app.claims import Claim,draft
from app.formatter import convert_bytes

def claim(**values):
    base=dict(passenger='Test Passenger',address='Test address',email='test@example.com',airline='Test airline',airline_address='Airline address',flight_number='ZZ123',flight_date='2026-01-01',booking_reference='TEST',departure='London',arrival='Paris',distance_km=500,arrival_delay_minutes=180,regime='UK261',departure_jurisdiction='UK',arrival_jurisdiction='EU',operating_carrier='UK',extraordinary_circumstances='no',details='Test disruption')
    return Claim(**(base|values))
@pytest.mark.parametrize('distance,minutes,amount',[(1500,180,220),(1501,180,350),(3500,180,350),(3501,180,260),(3501,239,260),(3501,240,520)])
def test_uk_boundaries(distance,minutes,amount):assert draft(claim(distance_km=distance,arrival_delay_minutes=minutes))['potential_compensation']['amount']==amount

def test_review_conditions():
    for changes in [{'arrival_delay_minutes':179},{'extraordinary_circumstances':'unknown'},{'extraordinary_circumstances':'yes'},{'departure_jurisdiction':'other','arrival_jurisdiction':'other','operating_carrier':'other'}]:assert draft(claim(**changes))['potential_compensation']['amount'] is None

def test_eu_intra_eu_band():assert draft(claim(regime='EU261',departure_jurisdiction='EU',arrival_jurisdiction='EU',distance_km=4000))['potential_compensation']['amount']==400

def test_formatter():
    out=convert_bytes(b'<h1>Hello</h1><script>steal()</script><p>World</p>','html','markdown');assert 'steal' not in out['content'];assert 'Hello' in out['content'];assert out['uploads_retained'] is False
    with pytest.raises(ValueError):convert_bytes(b'{broken','json','json')
    with pytest.raises(ValueError):convert_bytes(b'no PDF','pdf','markdown')

def test_pdf_text_extraction():
    import io
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
    writer=PdfWriter();page=writer.add_blank_page(width=300,height=200)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 20 100 Td (PDF extraction fixture) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream)
    buf=io.BytesIO();writer.write(buf)
    result=convert_bytes(buf.getvalue(),'pdf','markdown')
    assert 'PDF extraction fixture' in result['content']
