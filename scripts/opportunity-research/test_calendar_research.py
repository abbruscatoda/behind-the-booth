"""Regression tests for existing lead research and safe calendar-to-form publication."""
import unittest,json
from datetime import datetime,timezone
from unittest.mock import patch
from verifier import Document
import discovery
from form_discovery import verify_public_form

NOW=datetime(2026,11,16,17,tzinfo=timezone.utc)
ROOT='https://www.trianglepopup.com/applications'
CAL='https://www.trianglepopup.com/events'
EVENT='https://www.trianglepopup.com/events/holiday-artisan-market'
FORM='https://form.jotform.com/233513866839165'
STRUCTURED={
 '@type':'Event','name':'Raleigh Holiday Artisan Market',
 'startDate':'2026-12-13T11:00:00-05:00',
 'endDate':'2026-12-13T16:00:00-05:00',
 'eventStatus':'https://schema.org/EventScheduled',
 'organizer':{'name':'Triangle Pop-Up'},
 'location':{'name':'Downtown Market Hall',
  'address':{'addressLocality':'Raleigh','addressRegion':'NC','streetAddress':'123 Main Street'}}
}
def form(date='December 13, 2026'):
 return ('<h1>Raleigh Holiday Artisan Market Vendor Application</h1>'
  '<p>Event: '+date+'</p><p>Application Deadline: November 25, 2026 at 5:00 PM ET</p>'
  '<p>Booth fee: $75</p><div role="button">Submit</div>')
class Fetch:
 def __init__(self,calendar_link=True,event_link=True,date='December 13, 2026'):
  self.pages={
   ROOT:'<a href="'+CAL+'">2026 events calendar</a><a href="'+FORM+'">Vendor Application</a>',
   CAL:'<a href="'+EVENT+'">Holiday market schedule</a>' if calendar_link else '<p>Calendar not available</p>',
   EVENT:'<script type="application/ld+json">'+json.dumps(STRUCTURED)+'</script>'
      +('<a href="'+FORM+'">Vendor Application</a>' if event_link else ''),
   FORM:form(date),
  }
  self.calls=[]
 def get(self,url):
  self.calls.append(url)
  if url not in self.pages:raise ValueError('Unsupported URL')
  return Document(self.pages[url]),'a'*64
class CalendarLeadTests(unittest.TestCase):
 def test_calendar_research_verifies_exact_event_and_form(self):
  fetch=Fetch()
  with patch.object(discovery,'SOURCES',[('Triangle Pop-Up','Raleigh',ROOT)]):
   found,leads,stats=discovery.discover_triangle(fetch,NOW,include_search=False)
  self.assertEqual(len(found),1)
  self.assertEqual(found[0]['policy'],'triangle-form-calendar-v2')
  self.assertEqual(found[0]['organizer_root'],ROOT)
  self.assertEqual(found[0]['calendar_url'],CAL)
  self.assertEqual(found[0]['candidate']['source_url'],EVENT)
  self.assertEqual(found[0]['candidate']['starts_on'],'2026-12-13')
  self.assertGreaterEqual(stats['discovery_calendar_pages'],2)
  self.assertEqual(stats['discovery_verified_public_forms'],1)

 def test_unlinked_event_page_cannot_publish(self):
  fetch=Fetch(calendar_link=False)
  with patch.object(discovery,'SOURCES',[('Triangle Pop-Up','Raleigh',ROOT)]):
   found,_,_=discovery.discover_triangle(fetch,NOW,include_search=False)
  self.assertEqual(found,[])

 def test_unlinked_form_cannot_publish(self):
  fetch=Fetch(event_link=False)
  with patch.object(discovery,'SOURCES',[('Triangle Pop-Up','Raleigh',ROOT)]):
   found,_,_=discovery.discover_triangle(fetch,NOW,include_search=False)
  self.assertEqual(found,[])

 def test_mismatched_form_date_is_not_auto_published(self):
  fetch=Fetch(date='December 14, 2026')
  with patch.object(discovery,'SOURCES',[('Triangle Pop-Up','Raleigh',ROOT)]):
   found,_,_=discovery.discover_triangle(fetch,NOW,include_search=False)
  self.assertEqual(found,[])

 def test_backlog_must_still_be_linked_from_official_source(self):
  fetch=Fetch()
  url='https://form.jotform.com/999999999999999'
  backlog=[{'source_url':ROOT,'target_url':url,'title':'Vendor Application','organizer':'Triangle Pop-Up','city':'Raleigh'}]
  with patch.object(discovery,'SOURCES',[('Triangle Pop-Up','Raleigh',ROOT)]):
   _,leads,stats=discovery.discover_triangle(fetch,NOW,include_search=False,backlog=backlog)
  self.assertNotIn(url,[x['target_url'] for x in leads])
  self.assertEqual(stats['discovery_backlog_leads'],1)

 def test_calendar_provenance_not_accepted_on_unlisted_route(self):
  fetch=Fetch()
  lead={'source_url':EVENT,'target_url':FORM,'curated_source_url':ROOT,'linking_page_url':'https://www.trianglepopup.com/unknown'}
  with patch.object(discovery,'SOURCES',[('Triangle Pop-Up','Raleigh',ROOT)]):
   self.assertIsNone(verify_public_form(lead,fetch,NOW))

if __name__=='__main__':unittest.main()
