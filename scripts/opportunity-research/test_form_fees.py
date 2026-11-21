"""Regression tests for official application fee extraction."""
import unittest
from form_fees import extract_labeled_fees


class FormFeeTests(unittest.TestCase):
    def test_wake_forest_real_form_wording(self):
        page = (
            "FEES AND PAYMENTS "
            "$28 NON-REFUNDABLE Application Fee is due at time of application. "
            "$35 Event Booth Fee is due at each market that you attend. "
            "All fees are NON-REFUNDABLE. "
            "No application will be considered without full payment of the "
            "$28 non-refundable application fee."
        )
        self.assertEqual(extract_labeled_fees(page),
                         {"application_fee": 28.0, "booth_fee": 35.0})

    def test_label_first_prices(self):
        self.assertEqual(extract_labeled_fees(
            "Application fee: $15.00; standard booth fee: $50 per event."),
            {"application_fee": 15.0, "booth_fee": 50.0})

    def test_incomplete_pricing_does_not_invent_an_application_fee(self):
        self.assertEqual(extract_labeled_fees(
            "Our new vendors pay a registration fee. Booth fee $35 each Saturday."),
            {"application_fee": None, "booth_fee": 35.0})

    def test_conflicting_booth_prices_stay_unconfirmed(self):
        self.assertEqual(extract_labeled_fees(
            "$25 booth fee for a small space. $50 booth fee for a large space."),
            {"application_fee": None, "booth_fee": None})

    def test_no_vendor_fees_from_ticket_or_donation_price(self):
        self.assertEqual(extract_labeled_fees(
            "Admission tickets $15, sponsorship $300, donation $10, apply as vendor."),
            {"application_fee": None, "booth_fee": None})

    def test_adjacent_amount_cannot_migrate_to_wrong_category(self):
        self.assertEqual(extract_labeled_fees(
            "$28 application fee $35 event booth fee"),
            {"application_fee": 28.0, "booth_fee": 35.0})


if __name__ == "__main__":
    unittest.main()
