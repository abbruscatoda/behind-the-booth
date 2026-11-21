"""Public form autopublishing requires independent, exact evidence."""
import unittest,json,io,contextlib
from datetime import datetime,timezone
from unittest.mock import patch
from verifier import Document
from form_discovery import verify_public_form,supported_form
import discovery
import run as worker

NOW=datetime(2026,11,16,17,tzinfo=timezone.utc)
SOURCE='https://www.trianglepopup.com/applications'
APP='https://form.jotform.com/233513866839165'
EVENT={
 '@type':'Event','name':'Raleigh Holiday Artisan Market',
 'startDate':'2026-12-13T11:00:00-05:00',
 'endDate':'2026-12-13T16:00:00-05:00',
 'eventStatus':'https://schema.org/EventScheduled',
 'organizer':{'name':'Triangle Pop-Up'},
 'location':{'name':'Downtown Market Hall',
   'address':{'addressLocality':'Raleigh','addressRegion':'NC','streetAddress':'123 Main Street'}}
}
def source(event=None,link=APP):
 e=event or EVENT
 return '<script type="application/ld+json">'+json.dumps(e)+'</script><a href="'+link+'">Vendor Application</a>'
def form(name='Raleigh Holiday Artisan Market',date='December 13, 2026',control='Submit',
     deadline='November 25, 2026 at 5:00 PM ET'):
 return '<h1>'+name+' Vendor Application</h1><p>Event: '+date+'</p><p>Application Deadline: '+deadline+'</p><p>Booth fee: $75</p><div role="button">'+control+'</div>'
class Fetch:
 def __init__(self,src=None,app=None):
  self.src=src or source()
  self.app=app or form()
  self.calls=[]
 def get(self,url):
  self.calls.append(url)
  return Document(self.src if url==SOURCE else self.app),'a'*64

class AutoPublicFormTests(unittest.TestCase):
 def test_verified_public_form_is_auto_publish_candidate(self):
  r=verify_public_form({'source_url':SOURCE,'target_url':APP},Fetch(),NOW)
  self.assertIsNotNone(r)
  self.assertEqual(r['policy'],'triangle-form-auto-v1')
  self.assertTrue(r['form_complete'])
  self.assertTrue(r['form_readable'])
  self.assertEqual(r['decision'],'publish')
  self.assertEqual(r['candidate']['title'],'Raleigh Holiday Artisan Market')
  self.assertEqual(r['candidate']['starts_on'],'2026-12-13')
  self.assertEqual(r['candidate']['booth_fee'],75)
  self.assertEqual(r['candidate']['market_slug'],None)
  self.assertEqual(r['research_quality']['fields']['identity']['status'],'confirmed')
  self.assertEqual(r['research_quality']['fields']['deadline']['status'],'confirmed')

 def test_discovery_promotes_strongly_verified_form_to_publish_candidate(self):
  pages=Fetch()
  with patch.object(discovery,'SOURCES',[('Triangle Pop-Up','Raleigh',SOURCE)]):
   found,leads,summary=discovery.discover_triangle(pages,NOW,include_search=False,include_calendars=False)
  self.assertEqual(len(found),1)
  self.assertEqual(found[0]['policy'],'triangle-form-auto-v1')
  self.assertEqual(summary['discovery_verified_public_forms'],1)
  self.assertEqual(len(leads),1)

 def test_exact_event_official_pdf_fills_missing_standard_fee(self):
  form_no_price=form().replace('<p>Booth fee: $75</p>','')
  document={
   'url':'https://www.trianglepopup.com/s/2026-holiday-vendor-fee-schedule.pdf',
   'hash':'b'*64,
   'text':'Raleigh Holiday Artisan Market December 13, 2026. Standard booth fee: $95.',
   'optional_fees':{},
  }
  receipts={'documents':[document],'linked_count':1,'readable_count':1,'blocked_count':0,'complete':True}
  with patch('form_discovery.inspect_official_fee_documents',return_value=receipts):
   result=verify_public_form({'source_url':SOURCE,'target_url':APP},Fetch(app=form_no_price),NOW)
  self.assertIsNotNone(result)
  self.assertEqual(result['candidate']['booth_fee'],95)
  self.assertEqual(result['fee_document_coverage']['readable'],1)
  self.assertEqual(result['fee_document_receipts'][0]['sha256'],'b'*64)

 def test_generic_fee_pdf_not_assumed_to_apply_to_specific_event(self):
  form_no_price=form().replace('<p>Booth fee: $75</p>','')
  document={
   'url':'https://www.trianglepopup.com/s/regular-market-fee-schedule.pdf',
   'hash':'b'*64,
   'text':'Regular vendor daily rate $25. Standard booth fee: $50. '
          'Different market and season.',
   'optional_fees':{},
  }
  with patch('form_discovery.inspect_official_fee_documents',return_value={
       'documents':[document],'linked_count':1,'readable_count':1,'blocked_count':0,'complete':True}):
   result=verify_public_form({'source_url':SOURCE,'target_url':APP},Fetch(app=form_no_price),NOW)
  self.assertIsNotNone(result)
  self.assertIsNone(result['candidate']['booth_fee'])

 def test_pdf_conflict_with_form_price_does_not_autopublish(self):
  document={
   'url':'https://www.trianglepopup.com/s/2026-holiday-vendor-fee-schedule.pdf',
   'hash':'b'*64,
   'text':'Raleigh Holiday Artisan Market December 13, 2026. Booth fee: $120.',
   'optional_fees':{},
  }
  with patch('form_discovery.inspect_official_fee_documents',return_value={
       'documents':[document],'linked_count':1,'readable_count':1,'blocked_count':0,'complete':True}):
   result=verify_public_form({'source_url':SOURCE,'target_url':APP},Fetch(),NOW)
  self.assertIsNone(result)

 def test_wrong_form_date_rejected(self):
  self.assertIsNone(verify_public_form({'source_url':SOURCE,'target_url':APP},Fetch(app=form(date='December 14, 2026')),NOW))

 def test_wrong_organizer_rejected(self):
  self.assertIsNone(verify_public_form({'source_url':SOURCE,'target_url':APP},
    Fetch(src=source(event={**EVENT,'organizer':{'name':'Unrelated Organizer'}})),NOW))

 def test_unlinked_form_rejected(self):
  self.assertIsNone(verify_public_form({'source_url':SOURCE,'target_url':APP},Fetch(src=source(link='https://form.jotform.com/233513866839166')),NOW))

 def test_unverified_date_or_name_rejected(self):
  self.assertIsNone(verify_public_form({'source_url':SOURCE,'target_url':APP},Fetch(app=form(name='Another Market')),NOW))
  self.assertIsNone(verify_public_form({'source_url':SOURCE,'target_url':APP},Fetch(src=source(event={**EVENT,'startDate':'2026-12-12T11:00:00-05:00'})),NOW))

 def test_deadline_must_be_future_dated_and_explicit_timezone(self):
  for deadline in ['November 10, 2026 at 5:00 PM ET','November 25, 2026 at 5:00 PM',
                   'December 14, 2026 at 5:00 PM ET']:
   with self.subTest(deadline=deadline):
    self.assertIsNone(verify_public_form({'source_url':SOURCE,'target_url':APP},Fetch(app=form(deadline=deadline)),NOW))

 def test_multipage_gated_or_closed_forms_cannot_publish(self):
  for content in [form(control='Next'), 'You need permission to access this form',
                  '<p>This form is no longer accepting responses</p>']:
   with self.subTest(content=content[:25]):
    self.assertIsNone(verify_public_form({'source_url':SOURCE,'target_url':APP},Fetch(app=content),NOW))

 def test_valid_url_allowlist(self):
  self.assertTrue(supported_form(APP))
  self.assertTrue(supported_form('https://pci.jotform.com/form/253207413592151'))
  self.assertFalse(supported_form(APP+'?prefill=private'))
  self.assertFalse(supported_form('https://pci.jotform.com/form/123?answer=private'))

 def test_worker_routes_verified_form_to_guarded_rpc(self):
  result=verify_public_form({'source_url':SOURCE,'target_url':APP},Fetch(),NOW)
  calls=[]
  class FakeDB:
   def rpc(self,name,body=None):
    calls.append(name)
    if name=='btb_research_context':return {'enabled':True,'items':[]}
    if name=='btb_research_discovery_backlog':return []
    if name=='btb_research_market_gaps':return {'markets':[],'count':0}
    if name=='btb_research_run':return 'run'
    if name=='btb_research_record_discovery_leads_v2':return {'saved':0,'approved_sources':len(discovery.SOURCES)}
    if name=='btb_research_finalize_discovery_leads':return {'resolved':0}
    if name=='btb_research_publish_form':
     assert body['p_result']['policy']=='triangle-form-auto-v1'
     return {'action':'publish','reason':'Verified form published.'}
    raise AssertionError('Unexpected RPC '+name)
  class FakeFetcher:
   def __init__(self,limit):self.limit=limit;self.requests=0
  with patch.object(worker,'Database',FakeDB),patch.object(worker,'Fetcher',FakeFetcher),patch.object(worker,'discover',return_value=([],[])),patch.object(worker,'discover_triangle',return_value=([result],[],{})),contextlib.redirect_stdout(io.StringIO()):
   worker.run(False)
  self.assertIn('btb_research_publish_form',calls)
  self.assertLess(calls.index('btb_research_record_discovery_leads_v2'),calls.index('btb_research_publish_form'))
  self.assertNotIn('btb_research_apply',calls)

if __name__=='__main__':unittest.main()
