import unittest
from datetime import datetime,timezone
from verifier import Document,Uncertain,valid_url
from google_forms import read_public_form
from first_night import verify_first_night,SOURCE,SHORT,FORM
from run import existing_result

NOW=datetime(2026,11,17,15,tzinfo=timezone.utc)
ITEM={'id':'x','title':'First Night Raleigh','starts_on':'2026-12-31','ends_on':'2026-12-31','application_url':SHORT,'market_name':'First Night Raleigh','market_city':'Raleigh','market_state':'NC'}
# Synthetic fixtures; prices below are parser tests, NOT First Night's real fees.
def form(body,control='Submit'):
 return Document('<h1>First Night Raleigh application — December 31, 2026</h1>'+body+f'<div role="button">{control}</div>')
PUBLIC=Document(f'<h1>First Night Raleigh</h1><p>December 31, 2026 in Raleigh.</p><p>Submit the application and a photo of your setup with a $200 (food vendor) or $50 (novelty vendor) refundable deposit by 5:00PM on NOVEMBER 20.</p><p>Checks will not be accepted. Application is not an agreement of acceptance.</p><a href="{SHORT}">Apply</a>')
class Fetch:
 def __init__(self,app):self.app=app;self.calls=[]
 def get(self,url):
  self.calls.append(url)
  if url==SOURCE:return PUBLIC,'a'*64
  if isinstance(self.app,Exception):raise self.app
  return self.app,'b'*64

class GoogleTests(unittest.TestCase):
 def test_exact_unconditional_prices_and_free_are_not_unknown(self):
  f=read_public_form(form('<p>Booth fee: $125.00</p><p>Application fee: $0.00</p><p>Refundable deposit: $40</p>'))
  self.assertEqual((f['booth_fee'],f['application_fee'],f['deposit']),(125,0,40));self.assertTrue(f['complete'])
 def test_tiered_prices_stay_in_notes_not_universal_amount(self):
  f=read_public_form(form('<p>Food vendor booth fee: $650. Novelty vendor booth fee: $300.</p><p>$200 food / $50 novelty refundable deposit.</p>'))
  self.assertIsNone(f['booth_fee']);self.assertIsNone(f['deposit']);self.assertIn('$650',f['fee_notes']);self.assertIn('$50',f['fee_notes'])
 def test_requirements_and_refund_conditions_are_preserved(self):
  f=read_public_form(form('<p>Vendors must carry insurance. Load-in is at 1 PM; all tents require weights.</p><p>No refunds after acceptance.</p>'))
  self.assertIn('insurance',f['eligibility']);self.assertIn('weights',f['eligibility']);self.assertIn('No refunds',f['fee_notes'])
 def test_conflicting_prices_require_review(self):
  f=read_public_form(form('<p>Booth fee: $100</p><p>Booth fee: $150</p>'));self.assertIsNone(f['booth_fee']);self.assertTrue(f['issues'])
 def test_partial_multipage_form_never_counts_as_complete(self):self.assertFalse(read_public_form(form('<p>Booth fee: $150</p>','Next'))['complete'])
 def test_hidden_script_disabled_and_respondent_values_not_facts(self):
  f=read_public_form(form('<script>Booth fee: $1</script><p hidden>Booth fee: $2</p><input value="Booth fee: $3"><p>Describe your business</p>'))
  self.assertIsNone(f['booth_fee']);self.assertEqual(f['fee_notes'],'')
 def test_signin_and_empty_form_are_not_public_forms(self):
  for text in ['You must sign in to access this content','Allow Google Forms access to your necessary cookies','You need permission','']:
   with self.assertRaises(Uncertain):read_public_form(Document(text))
 def test_closed_form_never_counts_as_active(self):self.assertTrue(read_public_form(Document('<p>This form is no longer accepting responses.</p>'))['closed'])
 def test_google_and_official_fetch_scope_is_narrow(self):
  for url in [SOURCE,FORM,SHORT,FORM+'?usp=send_form']:self.assertTrue(valid_url(url),url)
  for url in ['http://docs.google.com/forms/x','https://docs.google.com/document/d/x','https://accounts.google.com/signin',FORM+'?entry.1=test',SHORT+'?anything=1','https://www.artsplosure.org/sponsor','https://forms.gle.evil.com/x']:self.assertFalse(valid_url(url),url)
 def test_blocked_application_still_collects_public_deposits_and_cutoff(self):
  r=verify_first_night(ITEM,Fetch(Document('You must sign in to access this content')),NOW);self.assertEqual(r['decision'],'review')
  f=r['research_suggestions']['fields'];self.assertIn('$200',f['fee_notes']);self.assertIn('$50',f['fee_notes']);self.assertNotIn('deposit',f);self.assertNotIn('booth_fee',f)
  self.assertEqual(f['deadline'],'2026-11-20T17:00:00-05:00');self.assertIn('photo',f['eligibility']);self.assertFalse(r['research_suggestions']['form_readable'])
 def test_readable_form_collects_details_but_does_not_auto_publish_unvetted_adapter(self):
  r=verify_first_night(ITEM,Fetch(form('<p>Booth fee: $125</p><p>Application fee: $0</p><p>Insurance is required.</p>')),NOW)
  self.assertEqual(r['decision'],'review');self.assertEqual(r['research_suggestions']['fields']['booth_fee'],125);self.assertTrue(r['research_suggestions']['complete'])
 def test_source_network_failure_does_not_invent_suggestions(self):
  class Bad:
   def get(self,url):raise TimeoutError()
  with self.assertRaises(TimeoutError):verify_first_night(ITEM,Bad(),NOW)
 def test_form_identity_mismatch_never_copies_application_prices(self):
  app=Document('<h1>Other Market December 31, 2027</h1><p>Booth fee: $999</p><div role="button">Submit</div>')
  r=verify_first_night(ITEM,Fetch(app),NOW);self.assertNotIn('booth_fee',r['research_suggestions']['fields']);self.assertIn('no application facts',r['reason'])
 def test_changed_event_year_rejected(self):
  with self.assertRaises(Uncertain):verify_first_night({**ITEM,'starts_on':'2027-12-31','ends_on':'2027-12-31'},Fetch(form('')),NOW)
 def test_wrong_profile_rejected(self):
  with self.assertRaises(Uncertain):verify_first_night({**ITEM,'market_name':'Other Market'},Fetch(form('')),NOW)
 def test_dispatch_is_before_eventeny_and_unsupported_forms_are_explicit(self):
  r=existing_result(ITEM,{},Fetch(form('<p>Booth fee: $100</p>')),NOW);self.assertIn('research_suggestions',r)
  with self.assertRaisesRegex(Uncertain,'Unsupported Google Form'):existing_result({**ITEM,'application_url':'https://forms.gle/unknown'}, {},Fetch(form('')),NOW)

class WorkerRunTests(unittest.TestCase):
 def test_dry_run_includes_research_without_any_database_mutation(self):
  import run,io,json
  from unittest.mock import patch
  from contextlib import redirect_stdout
  calls=[]
  item={**ITEM,'automation_hold':False,'ends_on':'2099-12-31','updated_at':'x'}
  class DB:
   def rpc(self,name,body=None):
    calls.append(name)
    if name=='btb_research_context':return {'enabled':True,'items':[item]}
    raise AssertionError('Dry run attempted database mutation: '+name)
  class Read:
   requests=0;limit=120
   def __init__(self,**kwargs):pass
  result={'decision':'review','reason':'Sign-in-only application.','research_suggestions':{'source_url':SOURCE,'fields':{'fee_notes':'Category-specific deposits found.'}}}
  capture=io.StringIO()
  with patch.object(run,'Database',DB),patch.object(run,'Fetcher',Read),patch.object(run,'discover',return_value=([],[])),patch.object(run,'existing_result',return_value=result),redirect_stdout(capture):run.run(True)
  self.assertEqual(calls,['btb_research_context']);self.assertIn('research_suggestions',capture.getvalue());self.assertIn('proposed_review',capture.getvalue())

if __name__=='__main__':unittest.main()
