# Triangle discovery coverage

The scheduled worker now checks 40 curated organizer/application roots and 13 official event calendars. Regional search runs one query for each of the 24 communities in `verifier.CITIES`, rotates seasonal, artisan, food-truck, festival, and rolling-intake terms, and includes the current and following year.

When RSS search supplies irrelevant geography pages or no vendor results, up to six community queries per run use an independent read-only HTML search fallback. The fallback selection rotates across runs. Both providers have bounded response sizes, timeouts and failure reporting; neither provider supplies publication evidence. Eventeny application hits can lead back to their own structured event metadata for normal verification.

## Discovery and publication

Search results are hints. They do not establish identity, location, dates, fees, deadlines, or availability. Unknown organizer hosts are recorded in the private run summary and shown in Admin Opportunities under **New sources to investigate**. They are never fetched or approved automatically. Approved-host search hits must also have a live link from the curated organizer root before entering research.

Official calendars retain market/event leads even when no application is found. Such a lead does not mean applications are open. Fully verified opportunities continue through the existing database publication gates. Closed intake, waitlists, separate food-truck applications, missing evidence and inaccessible forms retain their established handling.

Per-calendar limits prevent a single organizer consuming all event/form capacity. Event pages, index pages, lead batches and organizer groups rotate between scheduled runs. Deferred-event counts and search failures are recorded. Failed official fetches are cached within a run so repeated links to a blocked page do not waste request capacity; a new run retries them. The overall source request cap is 480; existing-listing rechecks still run before broad discovery.

The registry/lead transaction now runs before discovery publication and diagnosis, so newly curated sources are available to the database publisher on their first saved run and newly inserted leads can receive diagnostics immediately. The existing secret-guarded v2 ingestion RPC is reused. The companion `sql/expand_triangle_calendar_discovery_sources.sql` extends the database publisher to the seven new exact calendar/root pairs and source-path patterns. It retains the original authorization, quality, date/deadline, hidden-market and manual-hold guards. This migration was applied to the connected project during implementation.

## Missed-event regressions

- Pop-Up Raleigh application root: capture the actual December waiting-list form, without inferring an open booth.
- Raleigh Museum holiday vendor notice: explicitly monitored; HTTP 403 remains an unresolved source rather than an assumed open opportunity.
- Triangle Pop-Up: retain the organizer closure notice and discover event/calendar leads without promoting a payment link or closed intake.
- Municipal news paths and CivicPlus numeric event URLs: recognize relevant market/festival link labels.

No crawler can guarantee every Triangle opportunity: private social posts, new organizers, search indexing delays and blocked applications remain limitations. The admin report makes those gaps visible instead of treating an empty search as complete coverage.

## Validation

Run `python3 -m unittest discover -s scripts/opportunity-research -p 'test_*.py'` and `npm run build`. Regression tests cover regional scope, query rotation, feed errors, unapproved hosts, live official-link provenance, calendar fairness, municipal links, and waiting-list discovery. Production workflow runs these tests before touching opportunity records.
