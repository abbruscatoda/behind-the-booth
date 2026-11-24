"""Triangle discovery auto-publishes only fully verified, organizer-linked events."""
import unittest
import io
import contextlib
import run as worker
from datetime import datetime,timezone
from unittest.mock import patch
import discovery
import verifier
from test_verifier import fixtures, SOURCE,APP

NOW=datetime(2026,11,16,tzinfo=timezone.utc)
ORGANIZER={'name':'Geek and Grub Market','url':'https://www.eventeny.com/company/geekandgrub/'}
SEED='https://www.geekandgrubmarket.com/vendorapplication'

class Pages:
 def __init__(self,missing_app_link=False):
  self.calls=[]
  event={'name':'New Triangle Holiday Market','organizer':ORGANIZER}
  source,app=fixtures(event=event,app_event=event)
  if missing_app_link:source=source.replace(APP, 'https://www.eventeny.com/events/vendor/?id=99999')
  self.docs={SEED:'<a href="'+SOURCE+'">December event</a>',
             SOURCE:source,APP:app}
 def get(self,url):
  self.calls.append(url)
  if url not in self.docs:raise ValueError('Untrusted URL')
  return verifier.Document(self.docs[url]),'a'*64

class DiscoveryTests(unittest.TestCase):
 def test_curated_sources_are_covered_by_the_https_allowlist(self):
  for name,city,url in discovery.SOURCES:
   with self.subTest(source=name):
    self.assertTrue(verifier.valid_url(url))
    self.assertIn(city.lower(),verifier.CITIES)
  self.assertGreaterEqual(len(discovery.SOURCES),20)

 def test_new_triangle_application_qualifies_for_safe_auto_publication(self):
  pages=Pages()
  with patch.object(discovery,'SOURCES',[('Geek and Grub','Durham',SEED)]):
   candidates,leads,stats=discovery.discover_triangle(pages,NOW,include_search=False,include_calendars=False)
  self.assertEqual(len(candidates),1)
  self.assertEqual(candidates[0]['decision'],'publish')
  self.assertEqual(candidates[0]['policy'],'triangle-eventeny-auto-v1')
  self.assertEqual(candidates[0]['research_quality']['fields']['identity']['status'],'confirmed')
  self.assertIsNone(candidates[0]['candidate']['market_slug'])
  self.assertEqual(candidates[0]['candidate']['organizer'],'Geek and Grub Market')
  self.assertEqual(stats['discovery_verified_candidates'],1)

 def test_real_worker_uses_guarded_autopublisher_for_new_verified_event(self):
  pages=Pages()
  with patch.object(discovery,'SOURCES',[('Geek and Grub','Durham',SEED)]):
   found,_,_=discovery.discover_triangle(pages,NOW,include_search=False,include_calendars=False)
  calls=[]
  class FakeDB:
   def rpc(self,name,body=None):
    calls.append((name,body))
    if name=='btb_research_community_sync':return {'sources':len(body['p_sources'])}
    if name=='btb_research_community_context':return {'leads':[]}
    if name=='btb_research_context':return {'enabled':True,'items':[]}
    if name=='btb_research_discovery_backlog':return []
    if name=='btb_research_market_gaps':return {'markets':[],'count':0}
    if name=='btb_research_run':return 'test-run'
    if name=='btb_research_publish_discovery':
     self_result=body['p_result']
     assert self_result['policy']=='triangle-eventeny-auto-v1'
     assert self_result['decision']=='publish'
     return {'action':'publish','reason':'Auto-published new verified market.'}
    raise AssertionError('Unexpected RPC '+name)
  class FakeFetcher:
   def __init__(self,limit):self.limit=limit;self.requests=0
  with patch.object(worker,'Database',FakeDB),patch.object(worker,'discover',return_value=([],[])),patch.object(worker,'discover_triangle',return_value=(found,[],{})),patch.object(worker,'Fetcher',FakeFetcher),contextlib.redirect_stdout(io.StringIO()):
   worker.run(False)
  self.assertIn('btb_research_publish_discovery',[name for name,_ in calls])
  self.assertNotIn('btb_research_apply',[name for name,_ in calls])

 def test_known_opportunity_does_not_consume_new_draft_slot(self):
  pages=Pages()
  with patch.object(discovery,'SOURCES',[('Geek and Grub','Durham',SEED)]):
   found,_,stats=discovery.discover_triangle(pages,NOW,include_search=False,include_calendars=False,known={(APP,'2026-11-29')})
  self.assertEqual(found,[])
  self.assertEqual(stats['discovery_verified_candidates'],0)

 def test_application_metadata_must_cover_this_exact_event_date(self):
  pages=Pages()
  event={'name':'New Triangle Holiday Market','organizer':ORGANIZER}
  source,app=fixtures(event=event,app_event={**event,
   'startDate':'2026-12-29T11:00:00-05:00',
   'endDate':'2026-12-29T15:00:00-05:00'})
  pages.docs[SOURCE]=source
  pages.docs[APP]=app
  with patch.object(discovery,'SOURCES',[('Geek and Grub','Durham',SEED)]):
   candidates,_,_=discovery.discover_triangle(pages,NOW,include_search=False,include_calendars=False)
  self.assertEqual(candidates,[])

 def test_event_must_link_this_exact_vendor_application(self):
  with patch.object(discovery,'SOURCES',[('Geek and Grub','Durham',SEED)]):
   candidates,leads,stats=discovery.discover_triangle(Pages(missing_app_link=True),NOW,include_search=False,include_calendars=False)
  self.assertEqual(candidates,[])

 def test_unconfirmed_google_application_becomes_lead_not_published_listing(self):
  form='https://docs.google.com/forms/d/e/1FAIpQLScPXt0euH9ziXcAR3tA9BkXTQ4qtnTK9V6aqttIYbxlittBlA/viewform'
  pages=Pages();pages.docs[SEED]='<a href="'+form+'">Vendor Application</a>'
  with patch.object(discovery,'SOURCES',[('Geek and Grub','Durham',SEED)]):
   candidates,leads,_=discovery.discover_triangle(pages,NOW,include_search=False,include_calendars=False)
  self.assertEqual(candidates,[])
  self.assertEqual(len(leads),1)
  self.assertEqual(leads[0]['target_url'],form)

 def test_external_urls_are_never_fetched_from_hints(self):
  pages=Pages()
  pages.docs[SEED]='<a href="https://other.example/vendor-application">Apply</a>'
  with patch.object(discovery,'SOURCES',[('Geek and Grub','Durham',SEED)]):
   _,leads,_=discovery.discover_triangle(pages,NOW,include_search=False,include_calendars=False)
  self.assertEqual(pages.calls,[SEED])
  self.assertEqual(len(leads),1)

 def test_vendor_directories_and_non_vendor_forms_are_filtered(self):
  irrelevant=[
   ('https://www.godaddy.com/websites/website-builder','Vendor application'),
   ('https://www.apexfarmersmarket.com/volunteer-application','Volunteer Application'),
   ('https://www.apexfarmersmarket.com/musician-application','Musician Application'),
   ('https://www.caryfarmersmarket.com/meet-our-vendors/','MEET OUR VENDORS'),
   ('https://www.caryfarmersmarket.com/booth-payments/','Booth Payment Forms'),
   ('https://www.geekandgrubmarket.com/vendors-faqs','Market Rules & Policies / FAQs'),
   ('https://www.apexfarmersmarket.com/applicationclose','Application Closed!'),
   ('https://www.trianglepopup.com/apply-to-work-with-us','Apply to Work with Us'),
   ('https://www.caryfarmersmarket.com/wp-content/uploads/2026/rules.pdf','Please read rules before applying')
  ]
  for url,label in irrelevant:
   with self.subTest(url=url):self.assertFalse(discovery.is_application_hint(url,label))
  relevant=[
   ('https://pci.jotform.com/form/253207413592151','2026 Fall Vendor Application'),
   ('https://www.apexfarmersmarket.com/apply','Apply Now'),
   ('https://blackfarmersmkt.org/be-a-vendor/','Be A Vendor'),
   ('https://www.trianglepopup.com/apply-to-be-a-vendor','Apply to be a Vendor'),
   ('https://shoplocalraleigh.org/brewgaloo/brewgaloo-applications/','Apply to Brewgaloo')
  ]
  for url,label in relevant:
   with self.subTest(url=url):self.assertTrue(discovery.is_application_hint(url,label))

 def test_source_page_cannot_create_self_link_lead(self):
  doc=verifier.Document('<a href="'+SEED+'">Vendor Application</a>')
  events,apps,leads=discovery.extract_links(doc,SEED)
  self.assertEqual(leads,set())

 def test_survey_teaching_artist_and_general_registration_not_applications(self):
  cases=[
   ('https://forms.gle/bTUNdKrSVG4HodyN7','community survey'),
   ('https://form.jotform.com/262795159298173','Call for Summer Teaching Artists'),
   ('https://www.hollyspringsnc.gov/1701','Programs & Registration')
  ]
  for url,label in cases:
   with self.subTest(url=url):self.assertFalse(discovery.is_application_hint(url,label))

 def test_known_published_form_not_rediscovered_as_a_lead(self):
  form='https://form.jotform.com/252944311617153'
  pages=Pages()
  pages.docs[SEED]='<a href="'+form+'">Call for Holiday Mini Mall Vendors</a>'
  with patch.object(discovery,'SOURCES',[('Artspace','Raleigh',SEED)]):
   _,leads,_=discovery.discover_triangle(pages,NOW,include_search=False,include_calendars=False,known={(form,'2026-12-13')})
  self.assertEqual(leads,[])

 def test_ssrf_and_hidden_urls_rejected(self):
  for url in ('http://example.com/vendors','https://127.0.0.1/app',
   'https://localhost/vendor','https://example.com:8080/vendors',
   'https://username:password@example.com/app','https://169.254.169.254/vendor',
   'https://abc.internal/vendor','https://example.com/vendor#secret'):
   with self.subTest(url=url):self.assertFalse(discovery.is_safe_lead_url(url))

 def test_soft_source_outage_does_not_stop_other_sources(self):
  pages=Pages()
  with patch.object(discovery,'SOURCES',[('Missing','Cary','https://www.caryfarmersmarket.com/vendor-application/'),('Geek and Grub','Durham',SEED)]):
   found,_,stats=discovery.discover_triangle(pages,NOW,include_search=False,include_calendars=False)
  self.assertEqual(len(found),1)
  self.assertEqual(len(stats['optional_source_failures']),1)

if __name__=='__main__':unittest.main()
