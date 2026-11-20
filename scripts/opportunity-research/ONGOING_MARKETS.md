# Ongoing opportunities — permanent worker rules

Every published, visible, non-sample **Explore Markets** profile that has an official website is eligible for a rotating ongoing-application audit, **even if it already has a dated event listing**. A recurring schedule alone never means that applications are open.

The verifier only creates a new opportunity when it independently confirms:
1. The approved official market website identifies the specific market.
2. That site directly links to its own vendor information page or application.
3. Its current text affirmatively offers rolling/year-round vendor intake.
4. The linked public form independently names the same market and exposes an enabled application control.
5. Neither the vendor page nor the form contradicts current intake with closure, waitlist-only, invitation-only, or dated-event language.

The worker will **never** infer event dates, booth availability, vendor eligibility, application deadlines, standard fees, deposits, or category acceptance from incomplete evidence. Unknown prices remain null. Coverage dates are internal verification horizons, not attendance dates.

The worker uses a bounded rotating batch of eight markets per run and preserves request capacity for rechecking existing published opportunities. Skipped/failed verifications are recorded in run diagnostics. Once a generic ongoing opportunity is published, the worker re-verifies its source chain on future runs; a changed application link requires review rather than silent replacement.

The database publisher is secret-gated and only accepts fresh source hashes and matching names, cities, approved websites, linked application platforms, and verified policy receipts. It refuses hidden/sample markets, duplicate linked markets, archived opportunities, incompatible existing ongoing listings and manual automation holds.

The Raleigh Market's existing custom verifier and other seasonal/recurring policies remain in place. Custom adapters can capture confirmed category-specific fees and eligibility; the generic adapter intentionally cannot.

When a market is closed or lacks an independently readable application, it remains a research lead, not a published "open" opportunity. Never bypass authentication or submit a form as part of verification.

**Tests:** `python3 -m unittest discover -s scripts/opportunity-research -p 'test_*.py'`.
**Scheduled workflow:** `.github/workflows/opportunity-research.yml`.
