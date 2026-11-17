import unittest,copy
from verifier import Document,verify,Uncertain
from category_rules import application_facts,availability_text
from research_quality import add_review_suggestions,apply_quality_gate
from test_verifier import fixtures,FakeFetcher,SOURCE,APP,NOW
BASE='<p>Deadline: Nov 29, 2026 11:59 pm (GMT-05:00) Eastern Time</p><a>Start Application</a>'
def check(rows,extra='',**changes):
 source,app=fixtures(app_text=BASE+extra+'<h2>Prices</h2><table>'+rows+'</table>',**changes)
 return verify(SOURCE,APP,FakeFetcher(source,app),NOW)
STANDARD='<tr><td>10x10 Space</td><td>$100</td><td>Non-refundable</td></tr>'
class OptionAvailabilityTests(unittest.TestCase):
 def test_sold_out_nonprofit_is_not_application_closure(self):
  r=check(STANDARD+'<tr><td>Non-Profit Partner</td><td>SOLD OUT</td></tr>');self.assertEqual(r['decision'],'publish');self.assertEqual(r['candidate']['availability'],'open');self.assertEqual(r['candidate']['booth_fee'],100);self.assertIn('Non-Profit Partner: price not published; marked unavailable.',r['candidate']['fee_notes'])
 def test_fully_booked_or_waitlist_sponsor_does_not_close_standard(self):
  for state in ['Fully booked','WAITLIST','Sold out']:
   r=check(STANDARD+f'<tr><td>Sponsor Booth</td><td>$350</td><td>{state}</td></tr>');self.assertEqual(r['decision'],'publish');self.assertEqual(r['candidate']['availability'],'open')
 def test_global_closure_outside_rows_still_closes(self):
  r=check(STANDARD,extra='<p>Applications are closed.</p>');self.assertEqual(r['decision'],'closed')
 def test_ambiguous_sold_out_text_is_reviewed_but_retains_facts(self):
  r=check(STANDARD,extra='<p>One booth sold out; confirm remaining availability.</p>');self.assertEqual(r['decision'],'review');self.assertIn('10x10 Space',r['candidate']['fee_notes'])
 def test_standard_sold_out_never_advertised_as_available_price(self):
  r=check('<tr><td>10x10 Space</td><td>$100</td><td>Sold out</td></tr><tr><td>Sponsor Booth</td><td>$350</td></tr>');self.assertEqual(r['decision'],'review');self.assertIsNone(r['candidate']['booth_fee'])
 def test_standard_conflicting_rows_need_review(self):
  r=check(STANDARD+'<tr><td>10x10 Space</td><td>$150</td></tr>');self.assertEqual(r['decision'],'review');self.assertIsNone(r['candidate']['booth_fee'])
 def test_explicit_zero_app_fee_and_deposit_are_typed(self):
  r=check(STANDARD+'<tr><td>Application fee</td><td>$0</td></tr><tr><td>Refundable deposit</td><td>$25</td></tr>');self.assertEqual(r['candidate']['application_fee'],0);self.assertEqual(r['candidate']['deposit'],25)
 def test_category_specific_deposit_never_becomes_universal(self):
  r=check(STANDARD+'<tr><td>Food truck deposit</td><td>$200</td></tr>');self.assertIsNone(r['candidate']['deposit']);self.assertIn('Food truck deposit: $200',r['candidate']['fee_notes'])
 def test_group_rate_never_replaces_price_cell(self):
  r=check(STANDARD+'<tr><td>Sponsor Booth</td><td>$350</td><td>Description says $300 per event; 4 events for $1000.</td></tr>');self.assertEqual(r['candidate']['booth_fee'],100);self.assertIn('Sponsor Booth: $350',r['candidate']['fee_notes']);self.assertIn('$300 per event',r['candidate']['fee_notes'])
 def test_actual_wording_variations_keep_weights_photos_and_restrictions(self):
  extra='<h2>About the application</h2><p>Bring your own 10 x 10 tent and 4-20 lb tent weights. SAND BAG TENT WEIGHTS FILLED WITH ROCKS OR SAND. Rain or shine.</p><h3>Additional information</h3><p>I certify that I am not a THC/CBD Vendor or Mobile Boutique. 20lb bagged tent weights per corner of my tent (MUST BE SAND FILLED BAGS).</p><h3>Picture requirements</h3><p>Each application must include at least 3 photos of your products, 1 photo of your booth set up, and 1 photo of your tent weights.</p>'
  r=check(STANDARD,extra);rules=r['candidate']['eligibility'];self.assertIn('Four 20 lb',rules);self.assertIn('THC/CBD',rules);self.assertIn('three product photos',rules);self.assertIn('rain or shine',rules)
 def test_series_deadline_is_flagged_even_on_last_event_date(self):
  r=check(STANDARD,app_event={'startDate':'2026-03-08T11:00:00-04:00','endDate':'2026-11-29T15:00:00-05:00'});self.assertIn('Series application deadline',r['candidate']['fee_notes'])
 def test_global_application_status_table_is_not_hidden_as_option(self):
  r=check(STANDARD+'<tr><td>Application status</td><td>Sold out</td></tr>');self.assertEqual(r['decision'],'review')
 def test_excessive_terms_require_review_not_silent_truncation(self):
  r=check(STANDARD+'<tr><td>Sponsor Booth</td><td>$350</td><td>$300 '+'many conditions '*200+'</td></tr>');self.assertEqual(r['decision'],'review');self.assertNotIn('many conditions',r['candidate']['fee_notes'])
 def test_review_proposal_preserves_binding_and_zero(self):
  r=check(STANDARD+'<tr><td>Application fee</td><td>$0</td></tr>',extra='<p>One booth sold out.</p>');item={**r['candidate'],'id':'i'};p=add_review_suggestions(item,r)['research_suggestions'];self.assertEqual(p['fields']['application_fee'],0);self.assertEqual(p['application_url'],APP);self.assertTrue(p['form_readable']);self.assertFalse(p['complete'])
 def test_changed_occurrence_cannot_prefill_other_record(self):
  r=check(STANDARD);self.assertNotIn('research_suggestions',add_review_suggestions({'application_url':APP,'starts_on':'2026-12-20','ends_on':'2026-12-20'},r))
if __name__=='__main__':unittest.main()
