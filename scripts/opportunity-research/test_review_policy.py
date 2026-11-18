"""Regression tests: a failed source read must not undo a prior approval."""
import unittest
from urllib.error import HTTPError, URLError
from review_policy import defer_inconclusive_review, transient_source_failure

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

class SourceFailureTests(unittest.TestCase):
    def test_network_timeout_is_transient(self):
        self.assertTrue(transient_source_failure(TimeoutError("timed out")))
        self.assertTrue(transient_source_failure(URLError("connection reset")))

    def test_server_errors_and_rate_limits_are_transient(self):
        for code in (408, 429, 500, 502, 503, 504):
            with self.subTest(code=code):
                self.assertTrue(transient_source_failure(
                    HTTPError("https://example.com", code, "failed", {}, None)
                ))

    def test_permission_errors_do_not_silently_pass(self):
        for code in (401, 403, 404):
            with self.subTest(code=code):
                self.assertFalse(transient_source_failure(
                    HTTPError("https://example.com", code, "failed", {}, None)
                ))

    def test_programmer_error_must_surface(self):
        self.assertFalse(transient_source_failure(KeyError("missing_field")))
        self.assertFalse(transient_source_failure(ValueError("Untrusted URL")))


if __name__ == "__main__":
    unittest.main()
