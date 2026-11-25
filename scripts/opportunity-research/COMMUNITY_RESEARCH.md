# Community and public Instagram discovery

The full GitHub worker runs twice daily. The source-sync workflow also processes fresh community applications every three hours and on demand. `community_sources.json` records verified organizers, individual venues, primary websites and public Instagram accounts across event seasons. A vendor repost can lead to the organizer's own application.

The companion **Find Triangle vendor calls** research automation uses public web search and primary-page reads. It does not rely on Bing RSS being a useful search engine. It records findings in `btb_private.community_discovery_inbox`; the worker validates them through `community_discovery.py` and the existing dedicated worker secret. The inbox is private, has no anonymous/member policies, and cannot publish by itself. Admin Opportunities exposes a separate admin-only research panel. Search-provider success with no relevant results remains an incomplete-coverage warning.

The worker adds eight targeted indexed-Instagram queries per run to the 24 community queries. This is public search, not a signed-in feed or Stories crawler. Reviewed venue checks use a separate 48-request Fetcher budget; they include bounded image alt captions embedded by organizers on their own sites. Those captions can reveal explicit closures. Empty or inaccessible pages never prove there are no openings.

The hosted RPC layer rejects bulk registry resets with SQLSTATE 21000. Community source resets and inbox reconciliation update one primary key at a time, matching the established official-source registry workaround. A local Postgres test alone does not reproduce this platform behavior; deployment verification must include a successful live worker/source-sync run.

## Receipt contract

A lead has `source_key`, canonical HTTPS `target_url`, `title`, `notes`, `proposal` and `receipts`. The research sweep writes only the private inbox in Supabase. The worker owns registry synchronization and publication.

### Finish verified discoveries in the same run

1. Prioritize the earliest application deadlines. Check the existing directory, published opportunities and private inbox for the same organizer, venue, dates and application. Reuse an existing market profile when it matches. For a traveling organizer, verify the event's actual venue and city and give each distinct market its own identity.
2. A missing watchlist entry is work for the researcher. Follow the organizer or venue's public links to the dated application. Verify the organizer, venue and address before registering the identity. A dated organizer-linked application can provide both event and intake evidence. Save the hub's actual link, its observed redirect and evidence of current intake. On shared hosts, register the exact organizer or event path. Avoid broad platform roots.
3. When the evidence qualifies, prepare the full proposal immediately. For a new venue, stage it under a null `source_key` with `proposal.reviewed_source_key` set to its proposed registry key. Then commit the verified identity and canonical URLs to `community_sources.json` on GitHub in the same run. Reuse verified entries for later editions and preserve the other organizers. The private proposal alone cannot register a source. After synchronization the worker matches the staged row to the active key, validates it, and reconciles that row with the published listing.
4. On a registry push, follow the **Sync reviewed discovery sources** workflow. For updated applications at existing sources, run that workflow on current main with `community_only=true`, or rerun the current-main sync job via the GitHub connector. A scheduled pass also picks up late arrivals. Re-read stale evidence, resolve verification errors and retry while the application is current. Confirm the matching published row and its effective status in `btb_public_opportunities` before reporting success.
5. Keep incomplete discoveries private with the exact missing fact. An unpublished fee or deposit can remain null. An organizer's explicit email or DM invitation is a complete application route. A dated vendor waitlist accepting requests qualifies as waitlist-only. A publicly dated future opening qualifies as announced. Re-read the organizer's application when that date arrives.

`proposal` contains the source's event `title`, `venue`, ISO `starts_on`, `ends_on`, `application_url`, `application_method` (`form`, `email`, `instagram`), and `application_contact` (only the explicit vendor email or reviewed lowercase Instagram username). Optional values are `opens_on`, date-only `deadline_date`, numeric `booth_fee`, `application_fee`, `deposit`, and plain-language `fee_notes`/`eligibility`. Unknown costs are null, never zero. An artist application never verifies food/beverage eligibility. Keep separate audiences and application windows separate.

Optional `pricing_options` preserve tiered prices rather than choosing an invented universal fee. Each option has `kind` (`booth`, `application`, `addon`), `label`, numeric `amount`, `unit` (`day`, `event`, `season`, `program`, `application`), `conditions`, boolean `applicable`, and exact receipt `source_url`. Preserve resident discounts, double spaces, shared spaces, addons and late fees. A conditional option is not a guarantee every vendor qualifies. Never divide a season price into an invented daily rate.

Each receipt has exact primary-page `url`, `role` (`event`, `intake`, `opening`, `application`, `fee`), `access: "public_read"`, actual ISO `checked_at`, and an event-scoped text excerpt (20–12,000 characters). Include the exact event name, explicit year/dates, venue, application-specific invitation, and relevant public link URLs. Extracted public hrefs may be appended as `Links: ...`. Do not manufacture quotes or add a date from another event. Search snippets, user screenshots and login walls are leads, never public-read receipts. A public Instagram post needs its verified `owner` username in both the receipt and page text; a repost is insufficient.

For an open web form, set `form_state: "accepting"` only when enabled public submission controls or explicit current application-window metadata plus a live Apply link were read. General interest/mailing-list forms, attendee tickets, closed forms and inaccessible later application stages are not verified current intake. No responses are entered or submitted; no account login is performed. For email/DM calls the exact event-scoped invitation must explicitly request vendor emails/messages. A general contact email is insufficient. Photos mentioning vendors do not prove any vendor spaces remain.

For a dated multi-page vendor waitlist, the public organizer's current waitlist invitation, its exact matching form and an enabled first-page Next control establish that vendors can join. Record which controls were observed. Only an explicit waiver supports a zero application charge. An optional last-minute waitlist or a waitlist formed after jurying does not close regular intake.

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
