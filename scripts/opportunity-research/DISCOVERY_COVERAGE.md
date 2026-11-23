# Triangle discovery coverage

The scheduled worker now checks 54 curated organizer/application roots and 23 official event calendars. Regional search runs one query for each of the 24 communities in `verifier.CITIES`, rotates seasonal, artisan, food-truck, festival, and rolling-intake terms, and includes the current and following year.

When RSS search supplies irrelevant geography pages or no vendor results, up to six community queries per run use an independent read-only HTML search fallback. The fallback selection rotates across runs. Both providers have bounded response sizes, timeouts and failure reporting; neither provider supplies publication evidence. Eventeny application hits can lead back to their own structured event metadata for normal verification.

## Discovery and publication

Search results are hints. They do not establish identity, location, dates, fees, deadlines, or availability. Unknown organizer hosts are recorded in the private run summary and shown in Admin Opportunities under **New sources to investigate**. They are never fetched or approved automatically. Approved-host search hits must also have a live link from the curated organizer root before entering research.

Official calendars retain market/event leads even when no application is found. Such a lead does not mean applications are open. Fully verified opportunities continue through the existing database publication gates. Closed intake, waitlists, separate food-truck applications, missing evidence and inaccessible forms retain their established handling.

Per-calendar limits prevent a single organizer consuming all event/form capacity. Event pages, index pages, lead batches and organizer groups rotate between scheduled runs. Deferred-event counts and search failures are recorded. Failed official fetches are cached within a run so repeated links to a blocked page do not waste request capacity; a new run retries them. The overall source request cap is 480; existing-listing rechecks still run before broad discovery.

The registry/lead transaction now runs before discovery publication and diagnosis, so newly curated sources are available to the database publisher on their first saved run and newly inserted leads can receive diagnostics immediately. The existing secret-guarded v2 ingestion RPC is reused. The companion `sql/expand_triangle_calendar_discovery_sources.sql` extends the database publisher to the seven new exact calendar/root pairs and source-path patterns. It retains the original authorization, quality, date/deadline, hidden-market and manual-hold guards. This migration was applied to the connected project during implementation. The companion run-summary migration raises the secret-guarded report limit from 12 KB to 64 KB; detailed new-source and unlinked-page samples are bounded and rotate between runs.

A fast source-sync deployment workflow validates the same reviewed registry before waiting for a full crawl. Handled SQL failures or missing registry confirmation fail explicitly; they cannot masquerade as a successful run with zero saved leads. The hosted database rejected the old multi-row registry reset with SQLSTATE 21000. `sql/serialize_discovery_registry_reset.sql` resets existing primary-key rows individually within the same atomic transaction; the authenticated deployment sync subsequently confirmed all 40 sources. RSS hints from unknown sites additionally need a vendor-intake signal and matching Triangle location, preventing generic geography/real-estate/Chicago-market results from being treated as useful discovery.

## Missed-event regressions

- Pop-Up Raleigh application root: capture the actual December waiting-list form, without inferring an open booth.
- Raleigh Museum holiday vendor notice: explicitly monitored; HTTP 403 remains an unresolved source rather than an assumed open opportunity.
- Triangle Pop-Up: retain the organizer closure notice and discover event/calendar leads without promoting a payment link or closed intake.
- Municipal news paths and CivicPlus numeric event URLs: recognize relevant market/festival link labels.

No crawler can guarantee every Triangle opportunity: private social posts, new organizers, search indexing delays and blocked applications remain limitations. The admin report makes those gaps visible instead of treating an empty search as complete coverage.

## Validation

Run `python3 -m unittest discover -s scripts/opportunity-research -p 'test_*.py'` and `npm run build`. Regression tests cover regional scope, query rotation, feed errors, unapproved hosts, live official-link provenance, calendar fairness, municipal links, and waiting-list discovery. Production workflow runs these tests before touching opportunity records.

## Vintage, retro and independent market coverage

`market_catalog.py` checks five explicitly reviewed identities on every worker run: NC Vintage Market at Haven Farm, NC Vintage Bazaar, The Patchwork Market, Rebus Sunday Funday Market, and Raleigh Retro Gamers Markets. Source identity/location evidence is refreshed before any new profile is created. Directory publication is independent of open vendor applications; closed intake does not erase a legitimate market or its reviews. The database uses a fixed reviewed identity map, refuses hidden/sample/conflicting profiles, preserves existing edits, and records source receipts privately.

The discovery registry also includes the Haven Farm venue calendar, official NC Vintage Market organizer page, and the Bazaar, Patchwork, Rebus and Raleigh Retro vendor sources. Vintage/thrift/flea/collectible intent is included in rotating regional searches. Eventbrite organizer fetches are scoped to the reviewed NC Vintage Market organizer; attendee tickets are not vendor applications.

Raleigh Retro Gamers currently embeds its vendor application on `/vendors/` (the old application URL redirects there). Its adapter checks the actual vendor form, enabled submission control, current intake statement and explicit free-application wording. It publishes general rolling intake, not a guaranteed event or booth. Booth fees stay unknown, the $0 is application-only, and the internal calendar-year verification horizon renews each year without fabricating event dates or a submission deadline. Closed-form evidence takes precedence over an old call for vendors. Workshop/retail-only forms, expired deadlines and social-media-only signups are not treated as confirmed open event applications.

The source-sync deployment job also verifies and publishes the reviewed catalog and supported Retro intake, so these data additions do not require a frontend/Vercel build. The companion catalog and intake SQL scripts are applied to the connected production database; all publishers retain the worker-secret authorization.

## Published field evidence and vendor-facing completeness

Each worker run also audits optional fields on existing, visible published applications with its own bounded request budget. `fact_research.py` follows the exact organizer/application relationship and directly linked fee/rule documents. `opportunity-facts.yml` runs the same pass immediately when these rules change. It cannot publish/open a listing or override a manual hold.

- Save date-only application deadlines as calendar dates with source evidence. Display the date without inventing 11:59 PM; close on the following local day. Event dates, opening dates and conflicting dates do not qualify.
- Keep guest-day, attendance-tier, season-plan, resident-discount and application charges separate. Budget filtering considers eligible day/event options, not a whole-season price divided into invented daily rates.
- Prefer the newest actually effective official rate sheet. Recognize reviewed government PDF download endpoints and ordinary link labels such as “Download Fees PDF”; follow only organizer-linked documents.
- Distinguish an unreadable/partial form from a separate application fee not identified in readable materials. Neither establishes that applying is free. Zero requires explicit application-specific evidence.
- Sample contracts are contextual reference only; their prices must never be promoted as confirmed rates for a future event.
- Store source URL/hash, checked time, applicability and conditions. Public receipts expire after seven days and are invalidated by source/application/date/price changes. Hidden markets and private admin material remain inaccessible.
- If previously sourced options or a calendar deadline disappear, keep the last still-valid evidence and record the regression for rechecking instead of silently deleting details.

Regression fixtures: `test_fact_research.py` and `scripts/test_opportunity_facts.mjs` cover the Wake Forest November 27 cutoff, Fuquay guest/season plans, Western Wake regular/craft separation, the newer State Farmers Market schedule, blocked forms, free-application wording, sample contracts, category exclusions and budget/deadline filters.

## Independent venues and historical flyer regressions (November 23, 2026)

The reviewed watchlist now includes Dogwood, Fairy Lights Bazaar, Hartwell, M.I.N.E./Krampus, GRL Market, North Hills Midtown Makers Market, Grasshopper Farms and Unhinged Coffee & Co. These are monitored source identities, not claims that applications are open. The two St. Nick of Time flyers describe the same historical event; GRL venues are kept separate so their reviews and application restrictions do not get mixed. Midtown Makers Market is distinct from Midtown Farmers Market.

`independent_markets.py` follows the reviewed GRL link hub, corroborates the exact venue/date against the explicit year on the current organizer calendar, and reads the public `window.form_data` JSON embedded in Monday WorkForms. It does not execute page JavaScript, submit an application, read responses, log in, or fetch private board APIs. Only visible published questions and enabled category choices are captured. Welcome-page fees are included. Missing/changed schemas and date restrictions remain unconfirmed. Explicit closures close existing automated listings; they cannot create new openings. Application fees, deposits and cutoffs stay unknown without evidence.

New GRL editions can be discovered from new public form IDs at the three reviewed venues. Shared Linktree trust is restricted to `/Grlmarket`; unrelated profile recommendations are ignored. WorkForms are restricted to their public 32-character form paths without prefilled inputs. The venue-specific Transfer food exclusion and conflicting setup wording, and Waverly beverage restrictions and conflicting end times, are surfaced for vendors.

The source-sync workflow publishes fresh catalog receipts and verified independent applications immediately. The regular scheduled worker also runs the reader and rechecks previously published applications. Both use the same secret-guarded publication function and retain hidden-market, manual-hold, stale-evidence and duplicate safeguards. General venue hire forms, attendee ticket links, craft-class registrations, employment forms, outdated fees in hidden confirmation messages and old social flyers are never treated as active vendor applications. Historical dates retain their original year; annual recurrence is not invented. Public-source failures are recorded for monitoring, not replaced with guessed facts.
