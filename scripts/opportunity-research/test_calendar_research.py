"""Dated calendar events must be independently linked to one valid vendor form."""
import json
import unittest
from datetime import datetime,timezone
from unittest.mock import patch
from verifier import Document
from form_discovery import verify_public_form
from calendar_research import discover_calendars,calendar_event_pages
import discovery
import run as worker

NOW=datetime(2026,11,16,17,tzinfo=timezone.utc)
ROOT='https://www.trianglepopup.com/applications'
CALENDAR='https://www.trianglepopup.com/events'
EVENT='https://www.trianglepopup.com/events/raleigh-holiday-artisan-market'
FORM='https://form.jotform.com/233513866839165'
CONFIG=('Triangle Pop-Up',ROOT,CALENDAR)
EVENT_DETAILS={
 '@type':'Event','name':'Raleigh Holiday Artisan Market',
 'startDate':'2026-12-13T11:00:00-05:00',
 'endDate':'2026-12-13T16:00:00-05:00',
 'eventStatus':'https://schema.org/EventScheduled',
 'organizer':{'name':'Triangle Pop-Up'},
 'location':{'name':'Downtown Market Hall',
  'address':{'addressLocality':'Raleigh','addressRegion':'NC',
             'streetAddress':'123 Main Street'}}}

def event_html(details=None,form_url=None):
 data=details if details is not None else EVENT_DETAILS
 link='<a href="'+form_url+'">Vendor Application</a>' if form_url else ''
 return '<script type="application/ld+json">'+json.dumps(data)+'</script>'+link

def form_html(name='Raleigh Holiday Artisan Market',event_date='December 13, 2026',extra=''):
 return '<h1>'+name+' Vendor Application</h1><p>Event: '+event_date+'</p>' + extra + (
  '<p>Application deadline: November 25, 2026 at 5:00 PM ET</p>'
  '<p>Booth fee: $75</p><button>Submit</button>')

class Pages:
 def __init__(self,root=None,calendar=None,event=None,form=None):
  self.pages={
   ROOT:root if root is not None else '<a href="'+FORM+'">Apply to this market</a>',
   CALENDAR:calendar if calendar is not None else '<a href="'+EVENT+'">Upcoming Holiday Market</a>',
   EVENT:event if event is not None else event_html(),
   FORM:form if form is not None else form_html(),
  }
  self.calls=[]
 def get(self,url):
  self.calls.append(url)
  if url not in self.pages:raise AssertionError('Unexpected external fetch: '+url)
  return Document(self.pages[url]),'a'*64

def lead():
 return {'source_url':EVENT,'target_url':FORM,'calendar_url':CALENDAR,'organizer_root':ROOT}

class CalendarResearchTests(unittest.TestCase):
 def discover(self,pages,known=None):
  with patch('calendar_research.CALENDARS',(CONFIG,)),patch.object(discovery,'SOURCES',[('Triangle Pop-Up','Raleigh',ROOT)]):
   return discovery.discover_triangle(pages,NOW,include_search=False,known=known)

 def test_fully_dated_event_and_form_can_publish(self):
  pages=Pages()
  with patch('calendar_research.CALENDARS',(CONFIG,)):
   result=verify_public_form(lead(),pages,NOW)
   self.assertIsNotNone(result)
   self.assertEqual(result['policy'],'triangle-form-calendar-v2')
   self.assertEqual(result['organizer_root'],ROOT)
   self.assertEqual(result['calendar_url'],CALENDAR)
   self.assertEqual(result['candidate']['source_url'],EVENT)
   found,leads,stats=self.discover(Pages())
  self.assertEqual(len(found),1)
  self.assertEqual(found[0]['decision'],'publish')
  self.assertEqual(found[0]['policy'],'triangle-form-calendar-v2')
  self.assertEqual(stats['calendar']['calendar_form_pairs'],1)
  self.assertEqual(stats['calendar']['calendar_event_pages_inspected'],1)

 def test_nested_calendar_index_can_publish_verified_form(self):
  index='https://www.trianglepopup.com/events/holiday'
  pages=Pages(calendar='<a href="'+index+'">Holiday events</a>')
  pages.pages[index]='<a href="'+EVENT+'">Raleigh holiday artisan market</a>'
  found,_,stats=self.discover(pages)
  self.assertEqual(len(found),1)
  self.assertEqual(found[0]['decision'],'publish')
  self.assertEqual(stats['calendar']['calendar_indexes_inspected'],1)

 def test_nested_calendar_unlinked_event_cannot_publish(self):
  index='https://www.trianglepopup.com/events/holiday'
  pages=Pages(calendar='<a href="'+index+'">Holiday events</a>')
  pages.pages[index]='<a href="https://www.trianglepopup.com/events/other">Different event</a>'
  with patch('calendar_research.CALENDARS',(CONFIG,)):
   self.assertIsNone(verify_public_form(lead(),pages,NOW))

 def test_calendar_must_link_exact_event_page(self):
  pages=Pages(calendar='<a href="https://www.trianglepopup.com/events/other">Other Market</a>')
  with patch('calendar_research.CALENDARS',(CONFIG,)):
   self.assertIsNone(verify_public_form(lead(),pages,NOW))

 def test_event_must_be_official_same_host(self):
  pages=Pages(calendar='<a href="https://untrusted.example/events/hijack">Apply now</a>')
  with patch('calendar_research.CALENDARS',(CONFIG,)):
   events,forms,stats=discover_calendars(pages)
  self.assertFalse(forms)
  self.assertEqual(stats['calendar_event_pages_inspected'],0)

 def test_official_application_link_must_match(self):
  pages=Pages(root='<a href="https://form.jotform.com/111111111111111">Apply</a>')
  with patch('calendar_research.CALENDARS',(CONFIG,)):
   self.assertIsNone(verify_public_form(lead(),pages,NOW))

 def test_form_cannot_claim_another_organizer(self):
  details={**EVENT_DETAILS,'organizer':{'name':'Different Company'}}
  pages=Pages(event=event_html(details))
  with patch('calendar_research.CALENDARS',(CONFIG,)):
   self.assertIsNone(verify_public_form(lead(),pages,NOW))

 def test_event_date_must_be_on_application(self):
  pages=Pages(form=form_html(event_date='December 14, 2026'))
  with patch('calendar_research.CALENDARS',(CONFIG,)):
   self.assertIsNone(verify_public_form(lead(),pages,NOW))

 def test_organizer_closed_all_applications_for_event_year(self):
  pages=Pages(root=(
   '<p>All 2026 applications have closed.</p>'
   '<a href="'+FORM+'">Vendor Application</a>'))
  with patch('calendar_research.CALENDARS',(CONFIG,)):
   self.assertIsNone(verify_public_form(lead(),pages,NOW))

 def test_seasonal_form_with_multiple_events_does_not_automatically_publish(self):
  pages=Pages(form=form_html(extra='<p>Also accepting December 20, 2026 vendors.</p>'))
  with patch('calendar_research.CALENDARS',(CONFIG,)):
   self.assertIsNone(verify_public_form(lead(),pages,NOW))

 def test_existing_calendar_listing_rechecks_organizer_and_date(self):
  existing={'verification_policy':'triangle-form-calendar-v2',
   'source_url':EVENT,'application_url':FORM,
   'starts_on':'2026-12-13','ends_on':'2026-12-13',
   'market_organizer':'Triangle Pop-Up'}
  with patch('calendar_research.CALENDARS',(CONFIG,)):
   result=worker.existing_result(existing,{},Pages(),NOW)
  self.assertEqual(result['decision'],'publish')
  self.assertEqual(result['policy'],'triangle-form-calendar-v2')

 def test_known_application_does_not_become_duplicate(self):
  found,_,stats=self.discover(Pages(),known={(FORM,'2026-12-13')})
  self.assertEqual(found,[])
  self.assertEqual(stats['discovery_verified_public_forms'],0)

if __name__=='__main__':unittest.main()
