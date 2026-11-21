"""Regression coverage: a documented $0 fee differs from a missing price."""
import unittest
from form_fees import explicitly_free_application, extract_labeled_fees

class FreeApplicationFeeTests(unittest.TestCase):
 def test_holiday_craft_form_says_no_application_fee(self):
  intro=("2026 Holiday/Craft Vendor Application. Join the South Durham Farmers Market "
   "for our Holiday Craft Markets! There's no application fee—just fill out the form below.")
  self.assertTrue(explicitly_free_application(intro))
  self.assertEqual(extract_labeled_fees(intro)['application_fee'],0)
  self.assertIsNone(extract_labeled_fees(intro)['booth_fee'])
 def test_explicit_zero_numeric_is_not_unknown(self):
  for text in ("Application fee: $0", "$0 application fee", "Application fee: $0.00"):
   with self.subTest(text=text):
    self.assertEqual(extract_labeled_fees(text)['application_fee'],0)
 def test_no_mentioned_fee_is_unknown(self):
  self.assertIsNone(extract_labeled_fees("Craft vendors may apply for two holiday dates.")['application_fee'])
 def test_regular_guest_fee_stays_thirty(self):
  self.assertEqual(extract_labeled_fees("Application fee: $30")['application_fee'],30)
 def test_conflicting_free_and_charged_claims_remain_unknown(self):
  self.assertIsNone(extract_labeled_fees("There is no application fee. Application fee: $30.")['application_fee'])
 def test_zero_application_fee_does_not_clear_booth_price(self):
  fees=extract_labeled_fees("There's no application fee. Booth fee: $65")
  self.assertEqual(fees['application_fee'],0)
  self.assertEqual(fees['booth_fee'],65)

if __name__=='__main__':unittest.main()
