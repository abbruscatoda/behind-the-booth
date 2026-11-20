"""Evidence-gated seasonal market publishing and diagnostic regression tests."""
import unittest
from urllib.error import HTTPError
from datetime import datetime,timezone
from unittest.mock import patch
from verifier import Document,Uncertain
import seasonal_research as seasonal
import deep_research as deep
import run as worker
import contextlib,io

NOW=datetime(2026,11,18,20,tzinfo=timezone.utc)
FORM='https://form.jotform.com/242064838372157'
WEST_FORM='https://forms.gle/DmuLW5ni7Bu3Avhj8'

FVG_MAIN='''<h1>Fuquay-Varina Growers Market</h1>
<p>2027 Regular Season: Apr 10 - Sep 4th</p>
<p>Located at the FV Chamber of Commerce, 121 N Main Street, Fuquay-Varina NC</p>
<a href="https://www.fvgrowersmarket.com/vendor-application">Become a vendor</a>'''
FVG_VENDOR='''<h1>Fuquay-Varina Growers Market — Become a Vendor</h1>
<p>Now Accepting Vendor Applications for our 2027 Season!</p>
<p>We are now accepting vendor applications for the 2027 Season which will start on April 10th through September 4th.</p>
<p>Conveniently located at 121 N. Main St. in Fuquay-Varina.</p>
<p>We are not able to accept MLM, boutiques, or non handcrafted items.</p>
<a href="https://form.jotform.com/242064838372157">New Vendor Application</a>
<a href="https://form.jotform.com/242064908535156">Returning Vendor Application</a>'''
FVG_FORM='''<h1>2027 NEW Vendor Application</h1>
<p>Saturdays, April 10th to September 4th</p>
<p>Full-time, $260 (22 Saturdays)</p>
<p>Part-time, $180 (11 Saturdays)</p>
<p>Guest $30 per day</p><button>Submit</button>'''

WW_MAIN='''<h1>Western Wake Farmers Market</h1><p>Open Saturdays year-round</p>
<p>Vendor Applications Rolling!</p>
<p>Applications are open for WWFM's 26/27 season!</p>
<p>Physical: 101 Town Hall Drive Morrisville NC</p>
<a href="https://westernwakefarmersmarket.org/apply">Vend With Us</a>'''
WW_VENDOR='''<h1>Vendor Application</h1>
<p>Applications are accepted on a rolling basis.</p>
<p>Physical: 101 Town Hall Drive Morrisville NC</p>
<a href="https://forms.gle/DmuLW5ni7Bu3Avhj8">Regular Vendor Application</a>'''
WW_FORM='<h1>Western Wake Farmers Market Vendor Application</h1><button>Submit</button>'

class Fetch:
 def __init__(self):
  self.pages={seasonal.FVG_ROOT:FVG_MAIN,seasonal.FVG_VENDOR:FVG_VENDOR,
   FORM:FVG_FORM,seasonal.WW_ROOT:WW_MAIN,seasonal.WW_VENDOR:WW_VENDOR,
   WEST_FORM:WW_FORM}
  self.requests=0
  self.limit=220
  self.calls=[]
 def get(self,url):
  self.calls.append(url);self.requests+=1
  if url not in self.pages:raise ValueError('Unlisted source')
  return Document(self.pages[url]),'f'*64

WAKE_FORM='https://docs.google.com/forms/d/e/1FAIpQLSfWwZrk_p8ilgzhOq8Ypkd5iad93JXktwbhLUr74wLfEOGwcA/viewform'
WAKE_ROOT=('<h1>Wake Forest Farmers Market</h1><p>Join us on Saturdays Year Round</p>'
 '<a href="'+seasonal.WF_VENDOR+'">Market Vendor Application</a>')
WAKE_VENDOR=('<h2>Regular Market Vendors</h2>'
 '<p>If you are interested in becoming a regular Market Vendor, please fill out the following application.</p>'
 '<iframe src="'+WAKE_FORM+'?embedded=true"></iframe>')
WAKE_FORM_HTML=('<h1>2026-2027 VENDOR APPLICATION</h1>'
 '<p>Wake Forest Farmers Market</p><p>$28 nonrefundable application fee</p>'
 '<p>$35 per-event booth fee</p><button>Next</button>')

class SeasonalTests(unittest.TestCase):
 def test_strong_fvg_evidence_generates_season_and_full_fee_range(self):
  result=seasonal.check_provider(seasonal.PROVIDERS[0],Fetch(),NOW)
  data=result['candidate']
  self.assertEqual(result['decision'],'publish')
  self.assertEqual(data['schedule_type'],'seasonal_application')
  self.assertEqual(data['starts_on'],'2027-04-10')
  self.assertEqual(data['ends_on'],'2027-09-04')
  self.assertEqual(data['application_url'],FORM)
  self.assertIsNone(data['booth_fee'])
  self.assertIsNone(data['deadline'])
  self.assertIn('$260',data['fee_notes'])
  self.assertIn('$30 per day',data['fee_notes'])

 def test_market_address_may_appear_on_one_official_page(self):
  pages=Fetch()
  pages.pages[seasonal.FVG_VENDOR]=FVG_VENDOR.replace('121 N. Main St.','Downtown Fuquay-Varina')
  result=seasonal.check_provider(seasonal.PROVIDERS[0],pages,NOW)
  self.assertEqual(result['candidate']['venue'],'121 N. Main St. (Chamber of Commerce parking lot)')

 def test_neither_page_can_omit_the_venue(self):
  pages=Fetch()
  pages.pages[seasonal.FVG_VENDOR]=FVG_VENDOR.replace('121 N. Main St.','Downtown')
  pages.pages[seasonal.FVG_ROOT]=FVG_MAIN.replace('121 N Main Street','Downtown')
  with self.assertRaises(Uncertain):
   seasonal.check_provider(seasonal.PROVIDERS[0],pages,NOW)

 def test_fvg_rejects_conflicting_dates_or_closed_forms(self):
  for bad in ('<p>Saturdays, April 11th to September 4th</p><button>Submit</button>',
              FVG_FORM.replace('<button>Submit</button>',''),
              FVG_FORM.replace('2027 NEW','2026 NEW'),
              FVG_FORM+'<p>Applications closed</p>'):
   with self.subTest(bad=bad[:40]):
    fetch=Fetch();fetch.pages[FORM]=bad
    with self.assertRaises(Uncertain):seasonal.check_provider(seasonal.PROVIDERS[0],fetch,NOW)

 def test_fvg_cannot_use_returning_vendor_form_as_new_application(self):
  fetch=Fetch()
  fetch.pages[seasonal.FVG_VENDOR]=FVG_VENDOR.replace('>New Vendor Application</a>','>Returning Vendor Application</a>')
  with self.assertRaises(Uncertain):seasonal.check_provider(seasonal.PROVIDERS[0],fetch,NOW)

 def test_embedded_year_round_market_uses_official_cross_page_evidence(self):
  fetch=Fetch()
  fetch.pages[seasonal.WF_ROOT]=WAKE_ROOT
  fetch.pages[seasonal.WF_VENDOR]=WAKE_VENDOR
  fetch.pages[WAKE_FORM]=WAKE_FORM_HTML
  result=seasonal.check_provider(seasonal.PROVIDERS[2],fetch,NOW)
  self.assertEqual(result['candidate']['schedule_type'],'rolling_market')
  self.assertEqual(result['candidate']['title'],'Wake Forest Farmers Market — Rolling Vendor Applications')
  self.assertEqual(result['application_access'],'readable_first_page')
  self.assertFalse(result['form_complete'])
  self.assertTrue(result['form_readable'])
  self.assertIn('$28',result['candidate']['fee_notes'])

 def test_embedded_year_round_can_use_exact_official_iframe_when_google_returns_401(self):
  from urllib.error import HTTPError
  fetch=Fetch()
  fetch.pages[seasonal.WF_ROOT]=WAKE_ROOT
  fetch.pages[seasonal.WF_VENDOR]=WAKE_VENDOR
  prior=fetch.get
  def blocked(url):
   if url==WAKE_FORM:raise HTTPError(url,401,'Unauthorized',{},None)
   return prior(url)
  fetch.get=blocked
  result=seasonal.check_provider(seasonal.PROVIDERS[2],fetch,NOW)
  self.assertEqual(result['application_access'],'http_auth_blocked')
  self.assertIsNone(result['application_hash'])
  self.assertFalse(result['form_readable'])

 def test_embedded_market_must_still_link_exact_vendor_page(self):
  fetch=Fetch()
  fetch.pages[seasonal.WF_ROOT]=WAKE_ROOT.replace(seasonal.WF_VENDOR,'/outdated')
  fetch.pages[seasonal.WF_VENDOR]=WAKE_VENDOR
  fetch.pages[WAKE_FORM]=WAKE_FORM_HTML
  with self.assertRaises(Uncertain):
   seasonal.check_provider(seasonal.PROVIDERS[2],fetch,NOW)

 def test_rolling_market_uses_internal_horizon_not_event_dates(self):
  result=seasonal.check_provider(seasonal.PROVIDERS[1],Fetch(),NOW)
  data=result['candidate']
  self.assertEqual(data['schedule_type'],'rolling_market')
  self.assertEqual(data['starts_on'],'2026-01-01')
  self.assertEqual(data['ends_on'],'2027-12-31')
  self.assertIsNone(data['deadline'])
  self.assertIn('not scheduled events',data['research_notes'])

 def test_western_wake_address_in_official_footer(self):
  fetch=Fetch()
  fetch.pages[seasonal.WW_ROOT]=WW_MAIN.replace(
   '<p>Physical: 101 Town Hall Drive Morrisville NC</p>',
   '<footer>Physical: 101 Town Hall Drive Morrisville NC</footer>')
  result=seasonal.check_provider(seasonal.PROVIDERS[1],fetch,NOW)
  self.assertEqual(result['candidate']['schedule_type'],'rolling_market')

 def test_western_wake_wrong_footer_address_still_rejected(self):
  fetch=Fetch()
  fetch.pages[seasonal.WW_ROOT]=WW_MAIN.replace('101 Town Hall Drive','909 Unknown Place')
  fetch.pages[seasonal.WW_VENDOR]=WW_VENDOR.replace('101 Town Hall Drive','909 Unknown Place')
  with self.assertRaises(Uncertain):
   seasonal.check_provider(seasonal.PROVIDERS[1],fetch,NOW)

 def test_official_rolling_source_can_publish_if_google_form_returns_401(self):
  fetch=Fetch()
  original=fetch.get
  def blocked(url):
   if url==WEST_FORM:raise HTTPError(url,401,'Unauthorized',{},None)
   return original(url)
  fetch.get=blocked
  result=seasonal.check_provider(seasonal.PROVIDERS[1],fetch,NOW)
  self.assertEqual(result['decision'],'publish')
  self.assertEqual(result['application_access'],'http_auth_blocked')
  self.assertFalse(result['form_readable'])
  self.assertFalse(result['form_complete'])
  self.assertIsNone(result['application_hash'])
  self.assertIn('blocked automated verification',result['candidate']['research_notes'])

 def test_unlinked_rolling_form_cannot_publish_with_401(self):
  fetch=Fetch()
  fetch.pages[seasonal.WW_VENDOR]=WW_VENDOR.replace(WEST_FORM,'https://forms.gle/ZZZZZZZZZZZ')
  with self.assertRaises((Uncertain,ValueError)):
   seasonal.check_provider(seasonal.PROVIDERS[1],fetch,NOW)

 def test_missing_rolling_claim_cannot_publish_if_form_returns_401(self):
  fetch=Fetch()
  fetch.pages[seasonal.WW_VENDOR]=WW_VENDOR.replace('Applications are accepted on a rolling basis.','Applications may open soon.')
  with self.assertRaises(Uncertain):
   seasonal.check_provider(seasonal.PROVIDERS[1],fetch,NOW)

 def test_http_500_is_not_accepted_as_form_auth_block(self):
  fetch=Fetch()
  original=fetch.get
  def broken(url):
   if url==WEST_FORM:raise HTTPError(url,500,'Server error',{},None)
   return original(url)
  fetch.get=broken
  with self.assertRaises(HTTPError):
   seasonal.check_provider(seasonal.PROVIDERS[1],fetch,NOW)

 def test_rolling_market_rejects_inaccessible_form(self):
  fetch=Fetch();fetch.pages.pop(WEST_FORM)
  with self.assertRaises(ValueError):seasonal.check_provider(seasonal.PROVIDERS[1],fetch,NOW)

 def test_deep_research_produces_reason_and_no_publication(self):
  lead={'source_url':seasonal.WW_ROOT,'target_url':seasonal.WW_VENDOR,
        'title':'Vend With Us'}
  result=deep.diagnose_one(lead,Fetch(),NOW)
  self.assertEqual(result['status'],'confirmed_rolling')
  self.assertIn('rolling',result['reason'].lower())

 def test_unlinked_form_is_not_assumed_open(self):
  fetch=Fetch();fetch.pages[seasonal.WW_ROOT]=WW_MAIN.replace(
   'href="https://westernwakefarmersmarket.org/apply"','href="/other"')
  lead={'source_url':seasonal.WW_ROOT,'target_url':seasonal.WW_VENDOR,
        'title':'Vend With Us'}
  result=deep.diagnose_one(lead,fetch,NOW)
  self.assertEqual(result['status'],'unlinked')

 def test_worker_dispatches_new_seasonal_market_to_guarded_rpc(self):
  confirmed=seasonal.check_provider(seasonal.PROVIDERS[0],Fetch(),NOW)
  calls=[]
  class DB:
   def rpc(self,name,body=None):
    calls.append(name)
    if name=='btb_research_context':return {'enabled':True,'items':[]}
    if name=='btb_research_discovery_backlog':return []
    if name=='btb_research_market_gaps':return {'markets':[],'count':0}
    if name=='btb_research_publish_seasonal':
     self_result=body['p_result']
     assert self_result['candidate']['schedule_type']=='seasonal_application'
     return {'action':'publish','reason':'Seasonal market verified.'}
    if name=='btb_research_run':return 'test-run'
    raise AssertionError('Unexpected RPC '+name)
  class FakeFetcher:
   def __init__(self,limit):self.limit=limit;self.requests=0
  with patch.object(worker,'Database',DB),patch.object(worker,'Fetcher',FakeFetcher),patch.object(worker,'discover',return_value=([],[])),patch.object(worker,'discover_triangle',return_value=([],[],{})),patch('seasonal_research.discover_seasonal',return_value=[confirmed]),patch('recurring_market.discover_recurring',return_value=[]),contextlib.redirect_stdout(io.StringIO()):
   worker.run(False)
  self.assertIn('btb_research_publish_seasonal',calls)
  self.assertNotIn('btb_research_apply',calls)

if __name__=='__main__':unittest.main()
