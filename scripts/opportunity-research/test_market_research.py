"""Official linked leads from one organizer can establish one dated opportunity."""
import json
import unittest
from datetime import datetime,timezone
from unittest.mock import patch
from verifier import Document
from market_research import investigate_groups
from form_discovery import verify_public_form
import discovery

NOW=datetime(2026,11,19,17,tzinfo=timezone.utc)
ROOT='https://www.trianglepopup.com/applications'
EVENT='https://www.trianglepopup.com/events/holiday-artisan-market'
HUB='https://www.trianglepopup.com/vendor-applications'
FORM='https://form.jotform.com/233513866839165'
META={'@type':'Event','name':'Raleigh Holiday Artisan Market',
 'startDate':'2026-12-13T11:00:00-05:00','endDate':'2026-12-13T16:00:00-05:00',
 'eventStatus':'https://schema.org/EventScheduled',
 'organizer':{'name':'Triangle Pop-Up'},
 'location':{'name':'Downtown Market Hall','address':{'addressLocality':'Raleigh',
     'addressRegion':'NC','streetAddress':'123 Main Street'}}}
ROOT_HTML='<a href="'+EVENT+'">Holiday market details</a><a href="'+HUB+'">Vendor applications</a>'
HUB_HTML='<a href="'+FORM+'">Vendor application for Raleigh Holiday Artisan Market</a>'
EVENT_HTML='<script type="application/ld+json">'+json.dumps(META)+'</script>'
FORM_HTML=('<h1>Raleigh Holiday Artisan Market Vendor Application</h1>'
 '<p>December 13, 2026</p><p>Application deadline: November 25, 2026 at 5:00 PM ET</p>'
 '<p>Booth fee: $75</p><button>Submit</button>')

class Fetch:
 def __init__(self):
  self.pages={ROOT:ROOT_HTML,EVENT:EVENT_HTML,HUB:HUB_HTML,FORM:FORM_HTML}
  self.requests=0;self.limit=300
 def get(self,url):
  self.requests+=1
  if url not in self.pages:raise ValueError('Unlisted source '+url)
  return Document(self.pages[url]),'a'*64

def leads():
 return [{'source_url':ROOT,'target_url':HUB,'title':'Vendor applications',
          'organizer':'Triangle Pop-Up','city':'Raleigh'},
         {'source_url':ROOT,'target_url':FORM,'title':'Apply',
          'organizer':'Triangle Pop-Up','city':'Raleigh'}]

class GroupInvestigationTests(unittest.TestCase):
 def discover(self,fetch,items=None):
  with patch.object(discovery,'SOURCES',[('Triangle Pop-Up','Raleigh',ROOT)]):
   pairs,stats=investigate_groups(items if items is not None else leads(),fetch)
   verified=[result for pair in pairs if (result:=verify_public_form(pair,fetch,NOW))]
  return pairs,stats,verified

 def test_combines_official_event_and_separate_application_hub(self):
  pairs,stats,verified=self.discover(Fetch())
  self.assertEqual(stats['grouped_organizers_researched'],1)
  self.assertEqual(len(verified),1)
  self.assertEqual(verified[0]['decision'],'publish')
  self.assertEqual(verified[0]['candidate']['title'],'Raleigh Holiday Artisan Market')
  self.assertEqual(verified[0]['candidate']['application_url'],FORM)

 def test_unlinked_saved_application_cannot_be_used(self):
  fetch=Fetch();fetch.pages[HUB]='<p>No longer linked to an application</p>'
  pairs,_,verified=self.discover(fetch)
  self.assertTrue(pairs)
  self.assertEqual(verified,[])

 def test_wrong_date_in_form_never_publishes(self):
  fetch=Fetch();fetch.pages[FORM]=FORM_HTML.replace('December 13, 2026','December 14, 2026')
  _,_,verified=self.discover(fetch)
  self.assertEqual(verified,[])

 def test_other_organizer_not_researched(self):
  entries=[{**leads()[0],'source_url':'https://untrusted.example/vendor'}]
  pairs,stats,verified=self.discover(Fetch(),entries)
  self.assertEqual(stats['grouped_organizers_researched'],0)
  self.assertFalse(pairs)

 def test_research_never_uses_old_unlinked_hub(self):
  fetch=Fetch();fetch.pages[ROOT]='<a href="'+EVENT+'">Holiday market details</a>'
  pairs,_,verified=self.discover(fetch)
  self.assertEqual(verified,[])
  self.assertFalse(any(p.get('application_index_url')==HUB for p in pairs))

if __name__=='__main__':unittest.main()
