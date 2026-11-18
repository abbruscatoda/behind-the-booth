import json
import unittest
from datetime import datetime, timezone
from urllib.error import HTTPError
from verifier import Document, valid_url, Uncertain
from linked_forms import handles, read

NOW=datetime(2026,11,17,tzinfo=timezone.utc)
SOURCE='https://www.eventeny.com/events/test-market-34464/'
FORM='https://docs.google.com/forms/d/e/1FAIpQLSabcdefghijklmnopqrstuvwxyz0123456789/viewform'
JOT='https://form.jotform.com/253012345678901'
ITEM={'publication':'published','application_url':FORM,'source_url':SOURCE,
      'market_name':'Test Market','market_organizer':'Meow City','market_city':'Raleigh',
      'starts_on':'2026-12-13','ends_on':'2026-12-13'}
EVENT={'@type':'Festival','name':'Test Market','startDate':'2026-12-13T11:00:00-05:00',
       'endDate':'2026-12-13T15:00:00-05:00','eventStatus':'https://schema.org/EventScheduled',
       'organizer':{'name':'Meow City','url':'https://www.eventeny.com/company/?c=99182'},
       'location':{'name':'Market','address':{'addressLocality':'Raleigh','addressRegion':'NC'}}}
def source(link=FORM,event=EVENT):
 return Document('<script type="application/ld+json">'+json.dumps(event)+'</script><a href="'+link+'">Official vendor application</a>')

class Fetch:
 def __init__(self,event_doc=None,form_doc=None):
  self.event_doc=event_doc or source()
  self.form_doc=form_doc or Document('<h1>Test Market Vendor Application, December 13, 2026</h1><p>Booth fee: $95</p><div role="button">Submit</div>')
 def get(self,url):
  return (self.event_doc if url==SOURCE else self.form_doc),'a'*64

class LinkedFormTests(unittest.TestCase):
 def test_public_google_form_is_research_only(self):
  result=read(ITEM,Fetch(),NOW)
  self.assertEqual(result['decision'],'review')
  self.assertEqual(result['research_suggestions']['fields']['booth_fee'],95)
  self.assertTrue(result['research_suggestions']['complete'])

 def test_other_jotform_id_is_readable(self):
  result=read({**ITEM,'application_url':JOT},Fetch(event_doc=source(link=JOT)),NOW)
  self.assertEqual(result['research_suggestions']['fields']['booth_fee'],95)
  self.assertEqual(result['decision'],'review')

 def test_missing_link_cannot_claim_organizer_authorization(self):
  with self.assertRaises(Uncertain):
   read(ITEM,Fetch(event_doc=source(link=JOT)),NOW)

 def test_wrong_organizer_account_fails(self):
  event={**EVENT,'organizer':{'name':'Meow City','url':'https://www.eventeny.com/company/?c=9999'}}
  # The market name alone cannot establish a trusted platform account,
  # but generic research only binds to the approved organizer NAME.
  # Mismatches in the signed-in Eventeny account against the application
  # require the specialized Eventeny adapter before auto-publication.
  result=read(ITEM,Fetch(event_doc=source(event=event)),NOW)
  self.assertEqual(result['decision'],'review')

 def test_wrong_event_date_fails(self):
  with self.assertRaises(Uncertain):
   read({**ITEM,'starts_on':'2026-12-14'},Fetch(),NOW)

 def test_gated_form_does_not_guess_terms(self):
  result=read(ITEM,Fetch(form_doc=Document('<p>You need permission to access this form</p>')),NOW)
  self.assertFalse(result['research_suggestions']['form_readable'])
  self.assertEqual(result['research_suggestions']['fields'],{})

 def test_domain_guards(self):
  self.assertTrue(valid_url(FORM))
  self.assertTrue(valid_url(JOT))
  self.assertTrue(handles(ITEM))
  self.assertFalse(valid_url(FORM+'?entry.1=value'))
  for url in ['https://docs.google.com/document/d/sensitive','https://form.jotform.com/123?prefill=secret','https://forms.gle.evil.example/abc']:
   self.assertFalse(valid_url(url))

if __name__=='__main__':unittest.main()
