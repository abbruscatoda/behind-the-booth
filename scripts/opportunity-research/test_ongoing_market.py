"""Official rolling-market verification contract: never infer a booked date."""
import unittest
from unittest.mock import patch
import run as worker
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
 def test_legacy_manual_rolling_record_uses_dedicated_verifier(self):
  item={'market_slug':'the-raleigh-market','schedule_type':'rolling_market',
        'verification_policy':'manual','source_url':SOURCE,
        'application_url':APPLICATION}
  result=worker.existing_result(item,{},Fetch(),datetime(2026,11,20,tzinfo=timezone.utc))
  self.assertEqual(result['decision'],'publish')
  self.assertEqual(result['policy'],POLICY)

 def test_closure_blocks_publishing(self):
  with self.assertRaises(Uncertain):
   verify_raleigh(Fetch(source=VENDOR+'<p>Temporary vendor applications are closed.</p>'))
 def test_changed_official_price_is_automatically_republished(self):
  result=verify_raleigh(Fetch(source=VENDOR.replace('$30/day','$35/day'),form=FORM.replace('$30/day','$35/day')))
  self.assertEqual(result['decision'],'publish')
  self.assertEqual(result['candidate']['availability'],'open')
  self.assertEqual(result['candidate']['booth_fee'],35)
  self.assertIn('$35',result['candidate']['fee_notes'])

 def test_jotform_price_punctuation_or_missing_price_cannot_downgrade_intake(self):
  for form in (
    FORM.replace('($50/weekend, $30/day)','($50 per weekend; $30 per day)'),
    FORM.replace("Outdoor 10'x20' ($50/weekend, $30/day)","Outdoor 10x20, ask about rates"),
    FORM.replace('($50/weekend, $30/day)','($50 / weekend — $30 / day)'),
  ):
   with self.subTest(form=form):
    result=verify_raleigh(Fetch(form=form))
    self.assertEqual(result['decision'],'publish')
    self.assertEqual(result['candidate']['booth_fee'],30)
    self.assertEqual(result['candidate']['availability'],'open')

 def test_confirmed_price_conflict_discloses_issue_without_closing_application(self):
  result=verify_raleigh(Fetch(form=FORM.replace('$30/day','$40/day')))
  self.assertEqual(result['decision'],'publish')
  self.assertEqual(result['candidate']['availability'],'open')
  self.assertIsNone(result['candidate']['booth_fee'])
  self.assertTrue(result['form_price_discrepancy'])
  self.assertIn('conflicting',result['candidate']['fee_notes'])

 def test_missing_rates_do_not_erase_rolling_intake(self):
  source=VENDOR.replace('Weekend $50 / 10’ x 20’ space','Current rates available from the office').replace('$30/day','contact us')
  result=verify_raleigh(Fetch(source=source))
  self.assertEqual(result['decision'],'publish')
  self.assertIsNone(result['candidate']['booth_fee'])

 def test_form_explicitly_closed_still_never_publishes_as_open(self):
  with self.assertRaises(Uncertain):
   verify_raleigh(Fetch(form=FORM+'<p>Form is closed</p>'))
 def test_unlinked_application_blocks_publishing(self):
  with self.assertRaises(Uncertain):
   verify_raleigh(Fetch(source=VENDOR.replace('href="'+APPLICATION+'"','href="https://example.com"')))
 def test_form_identity_mismatch_blocks_publishing(self):
  with self.assertRaises(Uncertain):
   verify_raleigh(Fetch(form=FORM.replace('The Raleigh Market','Other Market')))
if __name__=='__main__':unittest.main()
