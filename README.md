This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.


## Triangle-wide vendor opportunity discovery

The GitHub Actions workflow `.github/workflows/opportunity-research.yml` runs twice daily
when `BTB_RESEARCH_SCHEDULE=enabled`. A manual workflow run supports `dry_run`.

The worker first rechecks approved opportunities using their official source,
then looks for **new** vendor applications across 20 curated Triangle organizer
pages (`scripts/opportunity-research/discovery.py`) and optional public web
search hints for Raleigh, Durham, Cary/Apex, and Chapel Hill/Carrboro.

- Search results are **untrusted leads only**. Search snippets are never treated
  as evidence that an event is accepting vendors.
- A new Eventeny event must have a validated organizer account, exact dated
  Triangle location, a vendor application linked from the event itself,
  matching application metadata, an enabled application action, and a future
  deadline. **Fully verified new discoveries are automatically published** via a
  separate research-secret-protected Supabase RPC, creating a market profile
  and dated occurrence in one transaction. Existing profiles are reused only
  when the normalized market name, organizer and city agree; conflicting or
  hidden markets are not overwritten. New events never borrow unrelated reviews.
- Vendor-form links that lack independently confirmed event details enter the
  private **New vendor-application leads** queue on
  `/admin/opportunities`. Admins can open the official source, use the
  draft editor, mark reviewed, or ignore a lead.
- The worker also loads unresolved application leads saved on earlier runs via a
  private, research-secret-authorized Supabase RPC. Those leads are
  re-evaluated even when they would otherwise fall outside the current
  discovery slice. Crucially, the currently fetched official source must
  still link to the exact application; old or untrusted URLs are not evidence
  of an open market. The existing dated organizer-calendar verifier then
  attempts to match each form to a real upcoming event before automatic
  publication. The backlog RPC is versioned in
  `scripts/opportunity-research/sql/20261118_discovery_backlog_rpc.sql`.
- A discovery-source failure does not invalidate or unpublish existing
  previously approved listings. Optional search feeds may be unavailable
  or incomplete, so this system is not an exhaustive list of every
  possible Triangle event.
- URL fetching is restricted to enumerated HTTPS hosts; the worker never
  signs in, bypasses controls, pays fees, or submits applications.
- No third-party search API key is needed. The RSS search is opportunistic;
  the curated sources continue functioning without it. Current request
  budgets and per-run verified-candidate caps are in `discovery.py`.
- Deeper source-to-event matching also checks six curated official event
  calendars (Triangle Pop-Up, Night Market Company, Geek and Grub,
  Western Wake, Shop Local Raleigh, Chapel Hill). It follows bounded
  same-host event-detail pages and matches organizer-linked public forms
  to their exact upcoming event. A form must explicitly name the event
  and event date, expose Submit, and show a future event-specific cutoff
  before the dedicated `triangle-form-calendar-v2` policy may publish.
  Seasonal or multievent forms remain private leads if the individual date
  cannot be confirmed. Explicit year-wide organizer closures override
  apparently clickable old application forms.
- Calendar-backed published events are revalidated on later worker runs.
  Current calendar allowlists and matching code live in
  `calendar_research.py`, with guarded database changes in
  `sql/20261118_deep_calendar_form_publication.sql` and
  `sql/20261118_expand_calendar_source_gates.sql`.
- The private discovery-lead table and worker/admin RPCs must be installed
  before deploying the worker. See
  `scripts/opportunity-research/sql/20261118_triangle_discovery_leads.sql`
  and `scripts/opportunity-research/sql/20261118_verified_triangle_auto_publish.sql`.
  Public Google Forms and Jotform applications now qualify for automatic
  publication only when a single official organizer page has exact, scheduled
  Event metadata, that page links the precise public form, and the form itself
  contains the matching event name/date, enabled Submit, and an explicitly
  timezone-labelled future application cutoff. Unreadable, multi-page,
  season-wide, conflicting or gated forms remain private leads. The additional
  guarded RPC is versioned at
  `scripts/opportunity-research/sql/20261118_verified_public_form_auto_publish.sql`.
  Previously published form-backed events are rechecked against the same
  evidence, with quality regressions held for review.


### Recurring farmers market waitlists

A recurring vendor market may accept applications all year without promising an
available booth or a deadline. The worker has a separately scoped
`recurring-official-waitlist-v1` verifier in
`scripts/opportunity-research/recurring_market.py`. Its first reviewed
provider is the **Town of Holly Springs**. It independently checks the town's
market and vendor pages, season dates (May 2026–April 2027), food-only
eligibility, $20 application fee, explicit year-round waiting list and exact
municipally linked ManageMyMarket registration URL. The provider does **not**
log in or claim to verify individual applicant account access.

When the evidence passes, the worker reuses the existing official market
profile, creates a **recurring season** occurrence, and publishes a **waitlist
only** application with a null deadline through the dedicated
research-secret-gated `btb_research_publish_recurring` RPC. Public display
uses `schedule_type=recurring_season` so a season is not presented as a
single guaranteed event date. Ongoing runs recheck the same official sources.
If key source claims disappear or conflict, the existing listing is retained
for investigation rather than silently changed or incorrectly marked open.
The provider registry is intentionally conservative: other markets require
their own verified official-source adapter and tests before auto-publication.

Database migration:
`scripts/opportunity-research/sql/20261118_recurring_market_waitlist.sql`.
