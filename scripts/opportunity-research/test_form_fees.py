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

    def test_real_western_wake_craft_fair_first_page(self):
        from form_fees import extract_fee_conditions
        first_page=(
            "WWFM Craft Fair Vendor Registration. "
            "CRAFT FAIR FEES: "
            "$10 nonrefundable application fee, payable when application is "
            "submitted (waived for current vendors). "
            "$30 per event: 10'x10' booth fee, payable upon acceptance. "
            "See Table of Fees for options such as a second tent space or "
            "cooperative vending arrangement."
        )
        self.assertEqual(extract_labeled_fees(first_page),
                         {"application_fee": 10.0, "booth_fee": 30.0})
        self.assertEqual(extract_fee_conditions(first_page),{
            "application_fee_waived_for_current_vendors": True,
            "application_fee_nonrefundable": True,
            "booth_fee_due_on_acceptance": True,
            "booth_size_10x10": True,
        })

    def test_linked_pdf_addons_do_not_become_standard_booth_fee(self):
        from form_fees import extract_linked_fee_options
        official_pdf=(
            "Booth Fees Vendor Tier Attendance Daily Rate "
            "Regular Vendor $20 Seasonal or Part-Time Vendor $25 "
            "Guest Vendor $30 Additional Fees "
            "Second Space Fee Available if space permits $20 "
            "Co-op Vending Arrangement Fee Assessed per tent; "
            "see Rules for details. $10"
        )
        self.assertEqual(extract_linked_fee_options(official_pdf),{
            "second_space":20.0,"co_op_tent":10.0
        })
        self.assertIsNone(extract_labeled_fees(official_pdf)["booth_fee"])

    def test_a_fee_for_tickets_or_a_different_tier_is_not_event_booth_fee(self):
        text=("Admission tickets $30 per event. $10 craft application fee. "
              "Additional large 20x20 booth pricing requires contacting us.")
        self.assertEqual(extract_labeled_fees(text),{
            "application_fee":10.0,"booth_fee":None
        })

    def test_conflicting_per_event_booth_prices_are_not_guessed(self):
        self.assertIsNone(extract_labeled_fees(
           "$30 per event: 10x10 booth fee. $55 per event: 20x20 booth fee."
        )["booth_fee"])

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
