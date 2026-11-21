"""Directory identities are verified separately from current vendor intake."""
import unittest
from datetime import datetime,timezone
from verifier import Document,Uncertain,valid_url
from market_catalog import CATALOG,verify_catalog_entry,discover_catalog
from official_vendor_programs import verify_program,PROGRAMS
from test_official_vendor_programs import Fetch
NOW=datetime(2026,11,21,17,tzinfo=timezone.utc)
class Pages:
 requests=0;limit=100
 def __init__(self):
  texts={
   'nc-vintage-haven':'NC Vintage Market brings vintage sellers from the Triangle.',
   'nc-vintage-bazaar':'NC Vintage Bazaar at NC Fairgrounds with vintage vendors.',
   'patchwork-durham':'The Patchwork Market at Durham Armory. Vendor applications are closed.',
   'rebus-sunday':'REBUS SUNDAY MARKET is a curated market in Raleigh.',
   'raleigh-retro-markets':'Raleigh Retro Gamers hosts pop-up markets in the Triangle with vintage sellers.',
  }
  self.docs={CATALOG[key]['source']:value for key,value in texts.items()}
 def get(self,url):
  if url not in self.docs:raise IOError('Unavailable')
  return Document('<h1>'+self.docs[url]+'</h1>'),'a'*64
class CatalogTests(unittest.TestCase):
 def test_small_deployment_fetch_budget_still_checks_catalog(self):
  pages=Pages();pages.limit=16
  results,notes=discover_catalog(pages,NOW)
  self.assertEqual(len(results),5)
 def test_verified_profiles_do_not_imply_open_applications(self):
  results,notes=discover_catalog(Pages(),NOW)
  self.assertEqual(len(results),5);self.assertFalse(notes)
  for result in results:
   self.assertNotIn('candidate',result)
   self.assertNotIn('application_url',result)
   self.assertNotIn('availability',result)
 def test_closed_patchwork_application_does_not_hide_real_market(self):
  self.assertEqual(verify_catalog_entry('patchwork-durham',Pages(),NOW)['catalog_key'],'patchwork-durham')
 def test_missing_location_or_market_identity_is_not_enough(self):
  pages=Pages();pages.docs[CATALOG['nc-vintage-bazaar']['source']]='NC Vintage Bazaar is a store in Charlotte.'
  with self.assertRaises(Uncertain):verify_catalog_entry('nc-vintage-bazaar',pages,NOW)
 def test_one_blocked_source_does_not_block_other_verified_profiles(self):
  pages=Pages();del pages.docs[CATALOG['nc-vintage-haven']['source']]
  results,notes=discover_catalog(pages,NOW)
  self.assertEqual(len(results),4);self.assertEqual(len(notes),1)
 def test_eventbrite_fetch_scope_does_not_include_unreviewed_organizers(self):
  self.assertTrue(valid_url(CATALOG['nc-vintage-haven']['source']))
  self.assertFalse(valid_url('https://www.eventbrite.com/o/unknown-123456789'))
  self.assertFalse(valid_url('https://www.eventbrite.com/o/nc-vintage-market-121068658483?login=true'))
 def test_new_catalog_sources_are_approved(self):
  self.assertTrue(all(valid_url(cfg['source']) for cfg in CATALOG.values()))
class RetroProgramTests(unittest.TestCase):
 def test_active_application_publishes_intake_not_guaranteed_event(self):
  result=verify_program('raleigh-retro-vendor-intake',Fetch(),NOW)
  c=result['candidate']
  self.assertEqual(c['application_fee'],0)
  self.assertIsNone(c['booth_fee']);self.assertIsNone(c['deposit']);self.assertIsNone(c['deadline'])
  self.assertEqual(c['schedule_type'],'rolling_market')
  self.assertIn('not a guaranteed booth',c['eligibility'])
  self.assertEqual(result['form_state'],'public_questions_visible')
 def test_a_newsletter_submit_is_not_a_vendor_application(self):
  fetch=Fetch();url=PROGRAMS['raleigh-retro-vendor-intake']['application']
  fetch.docs[url]=fetch.docs[url].replace('Are you an Individual or a Business?','Newsletter email address')
  with self.assertRaises(Uncertain):verify_program('raleigh-retro-vendor-intake',fetch,NOW)
 def test_disabling_submit_prevents_publication(self):
  fetch=Fetch();url=PROGRAMS['raleigh-retro-vendor-intake']['application']
  fetch.docs[url]=fetch.docs[url].replace('type="submit"','type="submit" disabled')
  with self.assertRaises(Uncertain):verify_program('raleigh-retro-vendor-intake',fetch,NOW)
 def test_missing_free_statement_never_infers_zero(self):
  fetch=Fetch();url=PROGRAMS['raleigh-retro-vendor-intake']['application']
  fetch.docs[url]=fetch.docs[url].replace('NO COST associated with your application','free admission')
  with self.assertRaises(Uncertain):verify_program('raleigh-retro-vendor-intake',fetch,NOW)
 def test_explicit_closure_is_closed_not_open(self):
  fetch=Fetch();url=PROGRAMS['raleigh-retro-vendor-intake']['application']
  fetch.docs[url]+='<p>Applications are closed.</p>'
  result=verify_program('raleigh-retro-vendor-intake',fetch,NOW)
  self.assertEqual(result['candidate']['availability'],'closed')
 def test_annual_horizon_renews_without_inventing_event_dates(self):
  result=verify_program('raleigh-retro-vendor-intake',Fetch(),datetime(2027,1,3,tzinfo=timezone.utc))
  self.assertEqual(result['candidate']['starts_on'],'2027-01-01')
  self.assertEqual(result['candidate']['ends_on'],'2027-12-31')
