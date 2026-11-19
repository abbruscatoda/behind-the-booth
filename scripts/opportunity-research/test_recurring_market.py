"""Municipal recurring waitlist verification: never invent event dates or deadlines."""
import unittest
from datetime import datetime,timezone
from unittest.mock import patch
import recurring_market as recurring
from verifier import Document,Uncertain
import run as worker
import contextlib,io

NOW=datetime(2026,11,18,23,tzinfo=timezone.utc)
MAIN=(
 '<h1>Holly Springs Farmers Market</h1>'
 '<p>Open Every Saturday 9:00 a.m. - Noon!</p>'
 '<p>Please note that the Holly Springs Farmers Market is a "food only" market.</p>'
 '<p>Physical Address: 300 W. Ballentine St. Holly Springs, NC 27540</p>'
 '<p>Winter Hours Almost every Saturday Nov 2026 - April 2027. Exceptions in Nov./Dec.</p>')
VENDOR=(
 '<nav><a href="https://www.hollyspringsnc.gov/319/Farmers-Market">Farmers Market</a></nav>'
 '<h1>Become a Vendor 2026-2027</h1>'
 '<p>We are seeking farmers and producers from across North Carolina.'
 ' We accept applications all year long.</p>'
 '<p>Please <a href="https://managemymarket.com/VendorRegister.aspx?orgID=933">complete the application</a> to be considered for our waiting list.</p>'
 '<p>We are not currently accepting food trucks.</p>'
 '<p>You must have a tax ID number. If accepted you must provide proof of liability insurance.</p>'
 '<h2>Farmers Market Fees: Season 20(May 2026 - April 2027)</h2>'
 '<p>Extended Season Weekly Vendor (50 dates) $442 Every Saturday May through April with two exceptions for holidays or town events</p>'
 '<p>Winter Season Weekly Vendor (25 dates) $207</p>'
 '<p>Application Fee $20 Applies to new applications and renewals.</p>')
VISIT=(
 '<nav><a href="https://www.hollyspringsnc.gov/319/Farmers-Market">Farmers Market</a></nav>'
 '<h1>Plan Your Visit</h1><h2>Now open every Saturday year-round</h2>'
 '<p>The Farmers Market is located at 300 W. Ballentine St., '
 'in the northern part of the loop outside the Holly Springs Cultural Center.</p>'
 '<p>Exceptions in December for holidays and town events.</p>')
class MockFetcher:
 def __init__(self,main=MAIN,vendor=VENDOR,visit=VISIT):
  self.html={recurring.HOLLY_MARKET:main,recurring.HOLLY_VENDOR:vendor,recurring.HOLLY_VISIT:visit}
  self.calls=[]
 def get(self,url):
  self.calls.append(url)
  if url not in self.html:raise AssertionError('Untrusted URL: '+url)
  return Document(self.html[url]),'a'*64

class RecurringWaitlistTests(unittest.TestCase):
 def test_verified_season_uses_waitlist_and_no_deadline(self):
  result=recurring.check_recurring_provider(recurring.PROVIDERS[0],MockFetcher(),NOW)
  c=result['candidate']
  self.assertEqual(result['decision'],'publish')
  self.assertEqual(result['policy'],'recurring-official-waitlist-v1')
  self.assertEqual(c['availability'],'waitlist')
  self.assertIsNone(c['deadline'])
  self.assertEqual(c['schedule_type'],'recurring_season')
  self.assertEqual(c['starts_on'],'2026-05-01')
  self.assertEqual(c['ends_on'],'2027-04-30')
  self.assertEqual(c['application_fee'],20)
  self.assertEqual(c['booth_fee'],None)
  self.assertEqual(c['application_url'],recurring.HOLLY_APPLICATION)
  self.assertEqual(c['market_slug'],'holly-springs-farmers-market')

 def test_missing_real_vendor_registration_blocks_publication(self):
  vendor=VENDOR.replace(recurring.HOLLY_APPLICATION,'https://nchollyspringsweb.myvscloud.com/webtrac/web/splash.html')
  with self.assertRaises(Uncertain):
   recurring.check_recurring_provider(recurring.PROVIDERS[0],MockFetcher(vendor=vendor),NOW)

 def test_http_www_registration_variant_for_exact_organization(self):
  variant='http://www.managemymarket.com/vendorregister.aspx?orgID=933'
  vendor=VENDOR.replace(recurring.HOLLY_APPLICATION,variant)
  candidate=recurring.check_recurring_provider(recurring.PROVIDERS[0],MockFetcher(vendor=vendor),NOW)
  self.assertEqual(candidate['candidate']['application_url'],recurring.HOLLY_APPLICATION)

 def test_unrelated_organization_registration_is_rejected(self):
  for variant in ('https://managemymarket.com/VendorRegister.aspx?orgID=934',
                  'https://managemymarket.com/VendorRegister.aspx?orgID=933&token=abc',
                  'https://managemymarket.example/VendorRegister.aspx?orgID=933',
                  'https://managemymarket.com/Login.aspx?orgID=933'):
   with self.subTest(link=variant):
    vendor=VENDOR.replace(recurring.HOLLY_APPLICATION,variant)
    with self.assertRaises(Uncertain):
     recurring.check_recurring_provider(recurring.PROVIDERS[0],MockFetcher(vendor=vendor),NOW)

 def test_no_market_breadcrumb_is_not_independent_evidence(self):
  vendor=VENDOR.replace(recurring.HOLLY_MARKET,'https://www.hollyspringsnc.gov/1701')
  with self.assertRaises(Uncertain):
   recurring.check_recurring_provider(recurring.PROVIDERS[0],MockFetcher(vendor=vendor),NOW)

 def test_closed_waitlist_or_changed_fee_halts_publication(self):
  for changed in [VENDOR.replace('our waiting list','closed applications'),
                  VENDOR.replace('Application Fee $20','Application Fee $35'),
                  VENDOR.replace('seeking farmers and producers from across North Carolina','seeking all types of temporary service businesses'),
                  VENDOR.replace('Weekly Vendor (50 dates) $442','Weekly Vendor (50 dates) $500')]:
   with self.subTest(fragment=changed[-120:]):
    with self.assertRaises(Uncertain):
     recurring.check_recurring_provider(recurring.PROVIDERS[0],MockFetcher(vendor=changed),NOW)

 def test_visitor_page_must_confirm_actual_market_address(self):
  for visit in (VISIT.replace('300 W. Ballentine St.','128 S. Main St.'),
                VISIT.replace('Now open every Saturday year-round','Hours to be announced'),
                VISIT.replace(recurring.HOLLY_MARKET,'https://www.hollyspringsnc.gov/1701')):
   with self.subTest(page=visit[-130:]):
    with self.assertRaises(Uncertain):
     recurring.check_recurring_provider(recurring.PROVIDERS[0],MockFetcher(visit=visit),NOW)

 def test_past_season_must_not_remain_open(self):
  with self.assertRaises(Uncertain):
   recurring.check_recurring_provider(recurring.PROVIDERS[0],MockFetcher(),datetime(2027,5,2,tzinfo=timezone.utc))

 def test_provider_never_requests_unverified_manage_my_market_accounts(self):
  f=MockFetcher()
  recurring.check_recurring_provider(recurring.PROVIDERS[0],f,NOW)
  self.assertEqual(set(f.calls),{recurring.HOLLY_MARKET,recurring.HOLLY_VENDOR,recurring.HOLLY_VISIT})

 def test_worker_dispatches_recurring_policy_to_restricted_rpc(self):
  r=recurring.check_recurring_provider(recurring.PROVIDERS[0],MockFetcher(),NOW)
  called=[]
  class DB:
   def rpc(self,name,body=None):
    called.append(name)
    if name=='btb_research_context':return {'enabled':True,'items':[]}
    if name=='btb_research_run':return 'test-run'
    if name=='btb_research_discovery_backlog':return []
    if name=='btb_research_publish_recurring':
     assert body['p_result']['policy']==recurring.POLICY
     return {'action':'publish','reason':'Recurring verified waitlist published.'}
    raise AssertionError(name)
  class Fetcher:
   def __init__(self,limit):self.limit=limit;self.requests=0
  with patch.object(worker,'Database',DB),patch.object(worker,'Fetcher',Fetcher),patch.object(worker,'discover',return_value=([],[])),patch.object(worker,'discover_triangle',return_value=([],[],{})),patch.object(recurring,'discover_recurring',return_value=[r]),contextlib.redirect_stdout(io.StringIO()):
   worker.run(False)
  self.assertIn('btb_research_publish_recurring',called)

if __name__=='__main__':unittest.main()
