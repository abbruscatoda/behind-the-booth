# Community and public Instagram discovery

The existing GitHub worker continues twice daily. `community_sources.json` is a persistent reviewed watchlist of venue identities, canonical websites, public Instagram accounts, and venue boundaries. It survives closed events. Vendor repost accounts identify leads but cannot establish an organizer's current intake. Multi-venue or otherwise unresolved identities stay discovery-only.

The companion **Find Triangle vendor calls** research automation uses public web search and primary-page reads. It does not rely on Bing RSS being a useful search engine. It records findings in `btb_private.community_discovery_inbox`; the worker validates them through `community_discovery.py` and the existing dedicated worker secret. The inbox is private, has no anonymous/member policies, and cannot publish by itself. Admin Opportunities exposes a separate admin-only research panel. Search-provider success with no relevant results remains an incomplete-coverage warning.

The worker adds eight targeted indexed-Instagram queries per run to the 24 community queries. This is public search, not a signed-in feed or Stories crawler. Reviewed venue checks use a separate 48-request Fetcher budget; they include bounded image alt captions embedded by organizers on their own sites. Those captions can reveal explicit closures. Empty or inaccessible pages never prove there are no openings.

## Receipt contract

A lead has `source_key`, canonical HTTPS `target_url`, `title`, `notes`, `proposal` and `receipts`. Unknown organizers use a null `source_key` and remain private discoveries. Never change the reviewed watchlist, authorization, moderation holds or public opportunity rows from a research sweep.

`proposal` contains the source's event `title`, `venue`, ISO `starts_on`, `ends_on`, `application_url`, `application_method` (`form`, `email`, `instagram`), and `application_contact` (only the explicit vendor email or reviewed lowercase Instagram username). Optional values are `opens_on`, date-only `deadline_date`, numeric `booth_fee`, `application_fee`, `deposit`, and plain-language `fee_notes`/`eligibility`. Unknown costs are null, never zero. An artist application never verifies food/beverage eligibility. Keep separate audiences and application windows separate.

Optional `pricing_options` preserve tiered prices rather than choosing an invented universal fee. Each option has `kind` (`booth`, `application`, `addon`), `label`, numeric `amount`, `unit` (`day`, `event`, `season`, `program`, `application`), `conditions`, boolean `applicable`, and exact receipt `source_url`. Preserve resident discounts, double spaces, shared spaces, addons and late fees. A conditional option is not a guarantee every vendor qualifies. Never divide a season price into an invented daily rate.

Each receipt has exact primary-page `url`, `role` (`event`, `intake`, `opening`, `application`, `fee`), `access: "public_read"`, actual ISO `checked_at`, and an event-scoped text excerpt (20–12,000 characters). Include the exact event name, explicit year/dates, venue, application-specific invitation, and relevant public link URLs. Extracted public hrefs may be appended as `Links: ...`. Do not manufacture quotes or add a date from another event. Search snippets, user screenshots and login walls are leads, never public-read receipts. A public Instagram post needs its verified `owner` username in both the receipt and page text; a repost is insufficient.

For an open web form, set `form_state: "accepting"` only when enabled public submission controls or explicit current application-window metadata plus a live Apply link were read. General interest/mailing-list forms, attendee tickets, closed forms and inaccessible later application stages are not verified current intake. No responses are entered or submitted; no account login is performed. For email/DM calls the exact event-scoped invitation must explicitly request vendor emails/messages. A general contact email is insufficient. Photos mentioning vendors do not prove any vendor spaces remain.

Receipts expire after six hours for new publication; published listings still expire after seven days without rechecking. An announced opening never becomes open merely because its opening date arrives: it becomes Needs rechecking until a fresh application read verifies intake. Exact date-only cutoffs stay date-only and close on the following local day. Closed intake cannot create a new opportunity. Hidden profiles, duplicate applications, existing unrelated policies and manual holds remain protected. Missing evidence preserves prior sourced facts rather than guessing new ones.

## Known regressions

- Lazy Daze artist intake opens December 1, 2026; food vendors have a separate later application. Cary's apply-page event dates conflict with the current festival/ZAPP dates. Use the exact current application evidence and surface the discrepancy.
- Artsplosure's current linked ZAPP is 15072, while an older `/exhibit` page links expired 13932. Current ZAPP dates differ from the organizer's copied event prose. Do not reuse expired applications.
- Hartwell's current embedded social caption closes St. Nick intake on November 16. That override wins over Apply Today in the same caption.
- Triangle Pop-Up explicitly closes all 2026 applications. Attendee tickets and vendor interest lists do not reopen them.
- Front Paige's VIP ticket products are attendee purchases, not booth fees; its general vendor mailing list does not establish a specific open event.
- The Optimist has two venues. Do not invent an exact December date or substitute a general owner email for the separate vendor-call email in a screenshot.
- Nomadas, Bull City Treasure Hunt and Oak & Ink screenshots are discovery leads until the current organizer post/application can be read.
- 71 South is Knoxville, Tennessee; it is outside this site's region.

## Validation

Run the Python worker tests, `node --test scripts/test_community_discovery.mjs scripts/test_opportunity_application.mjs`, and the Next production build. Tests cover explicit email/DM calls, source ownership, stale receipts, exact dates, closures, interest lists, announced openings, membership redaction, price scope and moderation protection.
