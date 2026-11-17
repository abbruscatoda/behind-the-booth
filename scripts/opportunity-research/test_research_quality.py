import copy,unittest
from pathlib import Path
from verifier import Document
from category_rules import application_facts,research_categories
from artspace_details import form_details
from research_quality import build_quality,regression_issues,apply_quality_gate
from test_verifier import NOW,SOURCE,APP

ROOT=Path(__file__).parent/'fixtures'
def fixture(name):return Document((ROOT/name).read_text())
def result():return {'decision':'publish','checked_at':NOW.isoformat(),'candidate':{'application_url':APP,'source_url':SOURCE,'starts_on':'2026-11-29','ends_on':'2026-11-29','deadline':'2026-11-25T23:59:00-05:00','availability':'open','booth_fee':240,'application_fee':None,'deposit':None,'fee_notes':''},'category_evidence':{'categories':{'Services':{'status':'eligible'}}}}

class QualityTests(unittest.TestCase):
 def report(self):
  r=result();r['research_quality']=build_quality(r,fixture('makrs-options.html'),'Explicit setup requirements.');return r
 def test_synthetic_market_layout_finds_prices_conditions_and_requirements(self):
  app=fixture('makrs-options.html');facts=application_facts(app);self.assertEqual(facts['standard_fee'],240);self.assertIn('Four 20 lb',facts['requirements'])
  receipt,conflicts=research_categories(Document(''),app,SOURCE,APP,NOW,'a'*64,'b'*64);self.assertIn('Services',receipt['categories']);self.assertIn('Prior organizer discussion',receipt['categories']['Services']['note']);self.assertFalse(conflicts)
 def test_synthetic_form_layout_keeps_both_table_options(self):
  facts=form_details(fixture('artspace-options.html'));self.assertEqual(facts['booth_fee'],30);self.assertIn('full table $60',facts['fee_notes'])
 def test_report_covers_vendor_questions_and_has_sources_and_check_times(self):
  q=self.report()['research_quality'];self.assertEqual(set(q['fields']),{'identity','availability','categories','costs','requirements','deadline'})
  for field in q['fields'].values():self.assertIn(field['source_url'],[SOURCE,APP]);self.assertEqual(field['checked_at'],NOW.isoformat())
  self.assertEqual(q['fields']['categories']['status'],'partial');self.assertEqual(q['fields']['deadline']['status'],'confirmed')
 def test_changed_layout_does_not_turn_unknown_into_free_or_unrestricted(self):
  r=result();r['candidate']['booth_fee']=None;r['category_evidence']['categories']={};q=build_quality(r,fixture('changed-layout.html'))
  for field in ['categories','costs','requirements']:self.assertEqual(q['fields'][field]['status'],'unconfirmed')
 def test_disappearing_price_section_routes_existing_listing_to_review(self):
  old=self.report()['research_quality'];r=self.report();r['research_quality']['signals']['price_options']=0
  checked=apply_quality_gate({'previous_quality':old},r);self.assertEqual(checked['decision'],'review');self.assertIn('price options',checked['reason'])
 def test_optional_unknowns_are_allowed_for_a_new_listing(self):
  r=result();r['candidate']['booth_fee']=None;r['category_evidence']['categories']={};r['research_quality']=build_quality(r,fixture('changed-layout.html'))
  self.assertEqual(apply_quality_gate(None,r)['decision'],'publish')
 def test_missing_critical_receipt_or_availability_cannot_publish(self):
  self.assertEqual(apply_quality_gate(None,result())['decision'],'review')
  r=self.report();r['candidate']['availability']='needs_recheck';self.assertEqual(apply_quality_gate(None,r)['decision'],'review')
 def test_category_evidence_loss_is_detected(self):
  a=self.report()['research_quality'];b=copy.deepcopy(a);b['signals']['category_keys']=[];self.assertTrue(regression_issues(a,b))
 def test_price_change_is_not_itself_a_layout_failure(self):
  a=self.report()['research_quality'];r=self.report();r['candidate']['booth_fee']=260;self.assertEqual(apply_quality_gate({'previous_quality':a},r)['decision'],'publish')
 def test_identical_reports_pass_and_do_not_mutate_previous_receipt(self):
  r=self.report();old=copy.deepcopy(r['research_quality']);self.assertEqual(apply_quality_gate({'previous_quality':old},r)['decision'],'publish');self.assertEqual(old,r['research_quality'])
 def test_series_and_same_day_cutoffs_are_explicitly_unconfirmed(self):
  for deadline in ['2026-11-29T23:59:00-05:00','2026-12-18T23:59:00-05:00']:
   r=result();r['candidate']['deadline']=deadline;q=build_quality(r,Document(''));self.assertEqual(q['fields']['deadline']['status'],'unconfirmed')
 def test_prior_unknown_becoming_partial_is_an_improvement(self):
  r=self.report();a=copy.deepcopy(r['research_quality']);a['fields']['requirements']['status']='unconfirmed';self.assertFalse(regression_issues(a,r['research_quality']))
if __name__=='__main__':unittest.main()
