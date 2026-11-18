"""Organizer-bound Eventeny verification must never inherit MAKRS privileges."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import verifier
import run as worker
from test_verifier import fixtures, FakeFetcher, SOURCE, APP

NOW = datetime(2026, 11, 16, tzinfo=timezone.utc)
ITEM = {
 "id":"1","title":"Approved test market","publication":"published",
 "market_id":"existing-id","market_slug":"test-market","market_name":"Approved test market",
 "market_organizer":"Meow City","market_city":"Durham","market_state":"NC",
 "starts_on":"2026-11-29","ends_on":"2026-11-29",
 "source_url":SOURCE,"application_url":APP,
}
MEOW = {"name":"Meow City","url":"https://www.eventeny.com/company/?c=99182"}

class OtherOrganizerTests(unittest.TestCase):
 def pages(self, app_event=None, event=None, card=None, app_text=None):
  event_data={"organizer":MEOW,"name":"Approved test market"}
  if event:event_data.update(event)
  source,app=fixtures(event=event_data,app_event={"organizer":MEOW,"name":"Approved test market",**(app_event or {})},**({"card":card} if card else {}),**({"app_text":app_text} if app_text else {}))
  return FakeFetcher(source,app)

 def test_approved_other_organizer_verified(self):
  result=verifier.verify(SOURCE,APP,self.pages(),NOW,expected_item=ITEM)
  self.assertEqual(result["decision"],"publish")
  self.assertEqual(result["policy"],"eventeny-organizer-v1")
  self.assertEqual(result["candidate"]["organizer"],"Meow City")
  self.assertEqual(result["candidate"]["market_slug"],"test-market")

 def test_slug_profile_organizer_is_verified(self):
  event_organizer={'name':'Geek and Grub Market','url':'https://www.eventeny.com/company/geekandgrub/'}
  item={**ITEM,'market_organizer':'Geek and Grub Market'}
  event={'organizer':event_organizer,'name':'Approved test market'}
  source,app=fixtures(event=event,app_event={'organizer':event_organizer,'name':'Approved test market'})
  result=verifier.verify(SOURCE,APP,FakeFetcher(source,app),NOW,expected_item=item)
  self.assertEqual(result['decision'],'publish')
  self.assertEqual(result['policy'],'eventeny-organizer-v1')

 def test_slug_profile_account_mismatch_is_blocked(self):
  event_organizer={'name':'Geek and Grub Market','url':'https://www.eventeny.com/company/geekandgrub/'}
  other_organizer={'name':'Geek and Grub Market','url':'https://www.eventeny.com/company/otherorg/'}
  item={**ITEM,'market_organizer':'Geek and Grub Market'}
  source,app=fixtures(event={'organizer':event_organizer,'name':'Approved test market'},
      app_event={'organizer':other_organizer,'name':'Approved test market'})
  with self.assertRaises(verifier.Uncertain):
   verifier.verify(SOURCE,APP,FakeFetcher(source,app),NOW,expected_item=item)

 def test_slug_url_guards(self):
  self.assertEqual(verifier.eventeny_organizer_identity('https://www.eventeny.com/company/geekandgrub/'),('slug','geekandgrub'))
  self.assertEqual(verifier.eventeny_organizer_identity('https://eventeny.com/company/?c=27023'),('id','27023'))
  for url in ['https://eventeny.com/company/geekandgrub/?redirect=foo',
     'https://eventeny.com/company/geekandgrub/extra','https://eventeny.com/company/','https://eventeny.com/company/?c=123&x=1',
     'https://eventeny.com.evil.test/company/geekandgrub/','http://eventeny.com/company/geekandgrub/']:
   with self.subTest(url=url):self.assertIsNone(verifier.eventeny_organizer_identity(url))

 def test_wrong_eventeny_account_blocked(self):
  with self.assertRaises(verifier.Uncertain):
   verifier.verify(SOURCE,APP,self.pages(event={"organizer":{"name":"Meow City","url":"https://www.eventeny.com/company/?c=99999"}}),NOW,expected_item=ITEM)

 def test_application_account_must_match_event(self):
  with self.assertRaises(verifier.Uncertain):
   verifier.verify(SOURCE,APP,self.pages(app_event={"organizer":{"name":"Meow City","url":"https://www.eventeny.com/company/?c=11111"}}),NOW,expected_item=ITEM)

 def test_saved_market_organizer_mismatch_does_not_publish(self):
  with self.assertRaises(verifier.Uncertain):
   verifier.verify(SOURCE,APP,self.pages(),NOW,expected_item={**ITEM,"market_organizer":"Other organizer"})

 def test_event_location_must_match_saved_market(self):
  result=verifier.verify(SOURCE,APP,self.pages(),NOW,expected_item={**ITEM,"market_city":"Cary"})
  self.assertEqual(result["decision"],"review")

 def test_date_mismatch_is_not_automatically_approved(self):
  result=verifier.verify(SOURCE,APP,self.pages(),NOW,expected_item={**ITEM,"starts_on":"2026-11-30"})
  self.assertEqual(result["decision"],"review")

 def test_closed_app_is_not_marked_open(self):
  result=verifier.verify(SOURCE,APP,self.pages(card=f'<div class="app-card"><a href="{APP}">Vendor application</a><p>Applications are closed</p></div>',app_text="<p>Applications are closed</p>"),NOW,expected_item=ITEM)
  self.assertEqual(result["decision"],"closed")

 def test_worker_routes_other_organizer_by_exact_link(self):
  fetcher=self.pages()
  result=worker.existing_result(ITEM,{},fetcher,NOW)
  self.assertEqual(result["policy"],"eventeny-organizer-v1")

if __name__=="__main__":
 unittest.main()
