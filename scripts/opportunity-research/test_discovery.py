"""Triangle discovery must produce review-only drafts, never auto-publish."""
import unittest
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

 def test_new_triangle_application_staged_as_review_only(self):
  pages=Pages()
  with patch.object(discovery,'SOURCES',[('Geek and Grub','Durham',SEED)]):
   candidates,leads,stats=discovery.discover_triangle(pages,NOW,include_search=False)
  self.assertEqual(len(candidates),1)
  self.assertEqual(candidates[0]['decision'],'review')
  self.assertIsNone(candidates[0]['candidate']['market_slug'])
  self.assertEqual(candidates[0]['candidate']['organizer'],'Geek and Grub Market')
  self.assertEqual(stats['discovery_reviewable_drafts'],1)

 def test_known_opportunity_does_not_consume_new_draft_slot(self):
  pages=Pages()
  with patch.object(discovery,'SOURCES',[('Geek and Grub','Durham',SEED)]):
   found,_,stats=discovery.discover_triangle(pages,NOW,include_search=False,known={(APP,'2026-11-29')})
  self.assertEqual(found,[])
  self.assertEqual(stats['discovery_reviewable_drafts'],0)

 def test_event_must_link_this_exact_vendor_application(self):
  with patch.object(discovery,'SOURCES',[('Geek and Grub','Durham',SEED)]):
   candidates,leads,stats=discovery.discover_triangle(Pages(missing_app_link=True),NOW,include_search=False)
  self.assertEqual(candidates,[])

 def test_unconfirmed_google_application_becomes_lead_not_published_listing(self):
  form='https://docs.google.com/forms/d/e/1FAIpQLScPXt0euH9ziXcAR3tA9BkXTQ4qtnTK9V6aqttIYbxlittBlA/viewform'
  pages=Pages();pages.docs[SEED]='<a href="'+form+'">Vendor Application</a>'
  with patch.object(discovery,'SOURCES',[('Geek and Grub','Durham',SEED)]):
   candidates,leads,_=discovery.discover_triangle(pages,NOW,include_search=False)
  self.assertEqual(candidates,[])
  self.assertEqual(len(leads),1)
  self.assertEqual(leads[0]['target_url'],form)

 def test_external_urls_are_never_fetched_from_hints(self):
  pages=Pages()
  pages.docs[SEED]='<a href="https://other.example/vendor-application">Apply</a>'
  with patch.object(discovery,'SOURCES',[('Geek and Grub','Durham',SEED)]):
   _,leads,_=discovery.discover_triangle(pages,NOW,include_search=False)
  self.assertEqual(pages.calls,[SEED])
  self.assertEqual(len(leads),1)

 def test_ssrf_and_hidden_urls_rejected(self):
  for url in ('http://example.com/vendors','https://127.0.0.1/app',
   'https://localhost/vendor','https://example.com:8080/vendors',
   'https://username:password@example.com/app','https://169.254.169.254/vendor',
   'https://abc.internal/vendor','https://example.com/vendor#secret'):
   with self.subTest(url=url):self.assertFalse(discovery.is_safe_lead_url(url))

 def test_soft_source_outage_does_not_stop_other_sources(self):
  pages=Pages()
  with patch.object(discovery,'SOURCES',[('Missing','Cary','https://www.caryfarmersmarket.com/vendor-application/'),('Geek and Grub','Durham',SEED)]):
   found,_,stats=discovery.discover_triangle(pages,NOW,include_search=False)
  self.assertEqual(len(found),1)
  self.assertEqual(len(stats['optional_source_failures']),1)

if __name__=='__main__':unittest.main()
