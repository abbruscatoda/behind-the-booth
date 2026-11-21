"""Generalized ongoing-market verifier should publish only independently matched forms."""
import unittest
from datetime import datetime,timezone
from urllib.error import HTTPError
from verifier import Document,Uncertain
from generic_ongoing import verify_generic_market,POLICY

ROOT="https://www.caryfarmersmarket.com/"
VENDOR="https://www.caryfarmersmarket.com/rolling-vendors"
APP="https://form.jotform.com/123456789012345"
MARKET={"slug":"cary-downtown-farmers-market","name":"Cary Downtown Farmers Market",
 "city":"Cary","website_url":ROOT}
HOME=f'<h1>Cary Downtown Farmers Market</h1><a href="{VENDOR}">Become a Vendor</a>'
PAGE=f'''<h1>Cary Downtown Farmers Market</h1>
<p>Vendor applications are accepted on a rolling basis. Apply as a vendor.</p>
<a href="{APP}">Vendor Application</a>'''
FORM='<h1>Cary Downtown Farmers Market Vendor Application</h1><button type="submit">Submit</button>'

class Fake:
 def __init__(self,home=HOME,page=PAGE,form=FORM):
  self.docs={ROOT:home,VENDOR:page,APP:form};self.requests=0;self.limit=360
 def get(self,url):
  self.requests+=1
  value=self.docs[url]
  if isinstance(value,Exception):raise value
  return Document(value),'a'*64

class RollingSourceTests(unittest.TestCase):
 def test_eligible_application_published_without_fabricated_price_or_dates(self):
  result=verify_generic_market(MARKET,Fake(),datetime(2026,11,20,tzinfo=timezone.utc))
  self.assertEqual(result['policy'],POLICY)
  c=result['candidate']
  self.assertEqual(c['application_url'],APP)
  self.assertEqual(c['source_url'],VENDOR)
  self.assertEqual(c['schedule_type'],'rolling_market')
  self.assertEqual((c['booth_fee'],c['application_fee'],c['deadline']),(None,None,None))
  self.assertEqual((c['starts_on'],c['ends_on']),('2026-01-01','2027-12-31'))
 def test_year_round_with_explicit_open_intake_is_ongoing(self):
  home=HOME.replace('Become a Vendor</a>','Become a Vendor</a><p>Open every week</p>')
  page=PAGE.replace('Vendor applications are accepted on a rolling basis. Apply as a vendor.',
                    'We are now accepting new vendors. Apply as a vendor.')
  result=verify_generic_market(MARKET,Fake(home=home,page=page))
  self.assertEqual(result['candidate']['availability'],'open')

 def test_current_intake_without_recurring_schedule_is_not_rolling(self):
  page=PAGE.replace('Vendor applications are accepted on a rolling basis. Apply as a vendor.',
                    'We are now accepting new vendors. Apply as a vendor.')
  with self.assertRaises(Uncertain):
   verify_generic_market(MARKET,Fake(page=page))

 def test_year_round_without_explicit_open_intake_is_not_enough(self):
  home=HOME+'<p>Open every week</p>'
  page=PAGE.replace('Vendor applications are accepted on a rolling basis. Apply as a vendor.',
                    'Learn about our vendors.')
  with self.assertRaises(Uncertain):
   verify_generic_market(MARKET,Fake(home=home,page=page))

 def test_closed_or_specific_event_not_ongoing(self):
  for warning in ["Vendor applications are closed.", "Application deadline on December 1, 2026"]:
   with self.subTest(warning=warning),self.assertRaises(Uncertain):
    verify_generic_market(MARKET,Fake(page=PAGE+"<p>"+warning+"</p>"))
 def test_no_unlinked_application(self):
  with self.assertRaises(Uncertain):
   verify_generic_market(MARKET,Fake(page=PAGE.replace(APP,"https://bad-site.example/form")))
 def test_unrelated_form_never_published(self):
  with self.assertRaises(Uncertain):
   verify_generic_market(MARKET,Fake(form=FORM.replace("Cary Downtown Farmers Market","Other Market")))
 def test_unreadable_form_not_published(self):
  with self.assertRaises(Uncertain):
   verify_generic_market(MARKET,Fake(form=HTTPError(APP,401,"Denied",{},None)))
 def test_homepage_must_name_exact_market(self):
  with self.assertRaises(Uncertain):
   verify_generic_market(MARKET,Fake(home=HOME.replace("Cary Downtown Farmers Market","Other Market")))
 def test_rolling_schedule_alone_not_enough(self):
  with self.assertRaises(Uncertain):
   verify_generic_market(MARKET,Fake(page=PAGE.replace("Vendor applications are accepted on a rolling basis.","We hold a market year-round.")))
if __name__=="__main__":unittest.main()
