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
  deadline. **New discoveries are drafts requiring administrator review**, not
  automatically published or linked to unrelated market reviews.
- Vendor-form links that lack independently confirmed event details enter the
  private **New vendor-application leads** queue on
  `/admin/opportunities`. Admins can open the official source, use the
  draft editor, mark reviewed, or ignore a lead.
- A discovery-source failure does not invalidate or unpublish existing
  previously approved listings. Optional search feeds may be unavailable
  or incomplete, so this system is not an exhaustive list of every
  possible Triangle event.
- URL fetching is restricted to enumerated HTTPS hosts; the worker never
  signs in, bypasses controls, pays fees, or submits applications.
- No third-party search API key is needed. The RSS search is opportunistic;
  the curated sources continue functioning without it. Current request
  budgets and per-run staging caps are in `discovery.py`.
- The private discovery-lead table and worker/admin RPCs must be installed
  before deploying the worker. See
  `scripts/opportunity-research/sql/20261118_triangle_discovery_leads.sql`.
