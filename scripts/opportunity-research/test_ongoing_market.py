"""Official rolling-market verification contract: never infer a booked date."""
import unittest
from datetime import datetime,timezone
from verifier import Document,Uncertain
from ongoing_market import verify_raleigh,ROOT,SOURCE,APPLICATION,POLICY

HOME=f'<h1>The Raleigh Market</h1><a href="{SOURCE}">Sell With Us</a>'
VENDOR=f'''<h1>The Raleigh Market</h1>
<p>4285 Trinity Rd, Raleigh, NC 27607</p>
<p>Saturday and Sunday 9 am - 5 pm</p>
<h2>TEMPORARY OUTDOOR VENDORS</h2>
<p>By Reservation (preferred method): Please fill out the
<a href="{APPLICATION}">Request to be a Vendor form</a>.
We will then send you our weekly call-for-vendors with further instructions.</p>
<p>There is no need to re-submit each week.</p>
<h2>RATES:</h2><p>Weekend $50 / 10’ x 20’ space</p>
<p>Saturday or Sunday only - $30/day</p>
<p>Food trucks and vendors wishing to sell food or beverages may NOT drop in--advanced reservation and approval is required.</p>'''
FORM='''<h1>The Raleigh Market</h1><p>Outdoor 10'x20' ($50/weekend, $30/day)</p>
<button type="submit">Submit Application</button>'''

class Fetch:
 def __init__(self,source=VENDOR,form=FORM):self.pages={ROOT:HOME,SOURCE:source,APPLICATION:form};self.calls=[]
 def get(self,url):
  self.calls.append(url)
  return Document(self.pages[url]),'a'*64

class RollingTests(unittest.TestCase):
 def test_verified_rolling_application_has_no_fabricated_event_or_deadline(self):
  reader=Fetch()
  result=verify_raleigh(reader,datetime(2026,11,20,tzinfo=timezone.utc))
  self.assertEqual(reader.calls,[ROOT,SOURCE,APPLICATION])
  self.assertEqual(result['policy'],POLICY)
  self.assertEqual(result['candidate']['schedule_type'],'rolling_market')
  self.assertIsNone(result['candidate']['deadline'])
  self.assertEqual(result['candidate']['booth_fee'],30)
  self.assertEqual(result['candidate']['starts_on'],'2026-01-01')
  self.assertEqual(result['candidate']['ends_on'],'2027-12-31')
  self.assertIn('$50',result['candidate']['fee_notes'])
 def test_closure_blocks_publishing(self):
  with self.assertRaises(Uncertain):
   verify_raleigh(Fetch(source=VENDOR+'<p>Temporary vendor applications are closed.</p>'))
 def test_changed_price_blocks_publishing(self):
  with self.assertRaises(Uncertain):
   verify_raleigh(Fetch(source=VENDOR.replace('$30/day','$35/day')))
 def test_unlinked_application_blocks_publishing(self):
  with self.assertRaises(Uncertain):
   verify_raleigh(Fetch(source=VENDOR.replace('href="'+APPLICATION+'"','href="https://example.com"')))
 def test_form_identity_mismatch_blocks_publishing(self):
  with self.assertRaises(Uncertain):
   verify_raleigh(Fetch(form=FORM.replace('The Raleigh Market','Other Market')))
if __name__=='__main__':unittest.main()
