import unittest
from verifier import Document,verify_artspace,Uncertain
from artspace_details import form_details,ConflictingTablePrices
import test_verifier as existing
from test_verifier import NOW

class TableDetailsTests(unittest.TestCase):
 def test_published_pair_and_explicit_requirements(self):
  d=Document('<div class="form-html">Table Fee: $25 for half a table (36 x 30) or $50 for a full 72 x 30 table. Vendors must be present for the full event. Table fees are due upon selection. No refunds of table fees. Artspace will not take a commission. Submissions will be juried; selections will be made on a rolling basis.</div>')
  r=form_details(d);self.assertEqual(r['booth_fee'],25);self.assertIn('half table $25.00; full table $50.00',r['fee_notes']);self.assertIn('full event',r['requirements']);self.assertIn('nonrefundable',r['requirements']);self.assertIn('due upon selection',r['requirements'])
 def test_radio_choices_read_from_space_question(self):
  d=Document('<li class="form-line"><span>Which space are you applying for? *</span><input type="radio" value="Half table - ($30)"><input type="radio" value="Full table - ($60)"></li>')
  r=form_details(d);self.assertEqual(r['booth_fee'],30);self.assertIn('$60.00',r['fee_notes'])
 def test_conflicting_prose_and_options_rejected(self):
  d=Document('<p>Table Fee: $25 for half a table or $50 for a full table.</p><fieldset><legend>Which space are you applying for?</legend><input type="radio" value="Half table ($30)"></fieldset>')
  with self.assertRaises(ConflictingTablePrices):form_details(d)
 def test_hidden_disabled_script_and_unrelated_radio_not_prices(self):
  d=Document('<div class="form-html" hidden>Table Fee: $1 for half a table or $2 for a full table.</div><script>Table Fee: $3 for half a table or $4 for a full table.</script><fieldset><legend>Which space are you applying for?</legend><input type="radio" disabled value="Half table ($5)"></fieldset><input type="radio" value="Full table ($6)">')
  self.assertIsNone(form_details(d)['booth_fee'])
 def test_missing_prices_not_zero(self):
  self.assertIsNone(form_details(Document('<p>Free to apply. Ask about tables.</p>'))['booth_fee'])
 def test_inverted_prices_rejected(self):
  with self.assertRaises(ConflictingTablePrices):form_details(Document('<p>Table Fee: $80 for half a table or $50 for a full table.</p>'))
 def test_no_generic_booth_range_for_single_option(self):
  r=form_details(Document('<fieldset><legend>Which space are you applying for?</legend><input type="radio" value="Full table ($60)"></fieldset>'))
  self.assertEqual(r['booth_fee'],60);self.assertIn('Full table: $60.00.',r['fee_notes']);self.assertNotIn('half table',r['fee_notes'])
 def test_complete_verifier_carries_facts_to_database_candidate(self):
  fixture=existing.ArtspaceTests();r=verify_artspace(fixture.item(),fixture.pages(form_extra='Table Fee: $25 for half a table or $50 for a full table. Vendors must be present for the full event. Table fees are due upon selection. No refunds of table fees.'),NOW)
  self.assertEqual(r['decision'],'publish');self.assertEqual(r['candidate']['booth_fee'],25);self.assertEqual(r['candidate']['application_fee'],0);self.assertIn('Table options:',r['candidate']['fee_notes']);self.assertIn('full event',r['candidate']['eligibility']);self.assertIn('different deadline',r['candidate']['fee_notes'])
if __name__=='__main__':unittest.main()
