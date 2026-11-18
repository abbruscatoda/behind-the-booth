"""Regression tests: a failed source read must not undo a prior approval."""
import unittest
from review_policy import defer_inconclusive_review

TRANSIENT = ("Official source could not be read reliably. "
             "The next successful run can resolve this automatically.")

class DeferredReviewTests(unittest.TestCase):
    def setUp(self):
        self.item = {
            "publication": "published",
            "availability": "open",
            "application_url": "https://forms.gle/e8JRmQUUcEirUzzY9",
            "starts_on": "2026-12-31",
            "ends_on": "2026-12-31",
        }

    def test_transient_error_on_published_listing_is_deferred(self):
        self.assertTrue(defer_inconclusive_review(self.item, {
            "decision": "review", "reason": TRANSIENT
        }))

    def test_draft_still_requires_review(self):
        self.assertFalse(defer_inconclusive_review(
            {**self.item, "publication": "draft"},
            {"decision": "review", "reason": TRANSIENT}
        ))

    def test_identity_mismatch_is_not_deferred(self):
        self.assertFalse(defer_inconclusive_review(self.item, {
            "decision": "review",
            "reason": "Organizer identity is not the trusted MAKRS account",
        }))

    def test_source_conflict_is_not_deferred(self):
        self.assertFalse(defer_inconclusive_review(self.item, {
            "decision": "review",
            "reason": "Application dates changed.",
            "candidate": {"starts_on": "2027-01-01"},
        }))

    def test_explicit_closure_is_not_deferred(self):
        self.assertFalse(defer_inconclusive_review(self.item, {
            "decision": "closed", "reason": "Applications closed"
        }))

    def test_first_night_unauthorized_form_is_deferred(self):
        self.assertTrue(defer_inconclusive_review(self.item, {
            "decision": "review",
            "policy": "artsplosure-google-v1",
            "reason": "Application could not be read by the public worker (HTTP 401).",
            "research_suggestions": {
                "form_readable": False,
                "application_url": self.item["application_url"],
                "starts_on": self.item["starts_on"],
                "ends_on": self.item["ends_on"],
            },
        }))

    def test_first_night_different_event_not_deferred(self):
        self.assertFalse(defer_inconclusive_review(self.item, {
            "decision": "review",
            "policy": "artsplosure-google-v1",
            "reason": "Application could not be read by the public worker (HTTP 401).",
            "research_suggestions": {
                "form_readable": False,
                "application_url": self.item["application_url"],
                "starts_on": "2027-12-31",
                "ends_on": "2027-12-31",
            },
        }))

if __name__ == "__main__":
    unittest.main()
