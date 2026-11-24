# Warm community design — restoration reference

The complete production version immediately before this visual redesign is commit
`e06931b6b28c8cad22b9a153462a0f5b6a9267bf` in `abbruscatoda/behind-the-booth`.

## Copy-and-paste restore request

> Restore Behind the Booth’s visual design from commit `e06931b6b28c8cad22b9a153462a0f5b6a9267bf`. Revert the redesign’s styling, fonts, imagery, and layout changes while preserving current data, authentication, worker rules, links, and functionality. Verify the result and redeploy.

## Scope

- The old appearance is the Modern Heritage version: cream, forest green,
  Georgia serif headings, square comparison cards, and the illustrated logo
  panel on the homepage.
- Restore only the presentation changes, comparing current files with the
  baseline. Preserve unrelated functional edits made after the redesign.
- Do not reset the branch or database to the old commit. A normal forward
  commit can restore the appearance without removing later work.
- Market website links belong on individual profiles, not directory cards.
- Preserve compact cards, title-triggered opportunity details, bookmark save
  controls, rating descriptors/colors, source-specific labels, and all review
  and application behavior.

## Redesign presentation files

- `src/app/globals.css`
- `src/app/layout.tsx`
- `src/app/page.tsx`
- `src/app/markets/page.tsx`
- `src/app/opportunities/page.tsx`
- `src/components/OpportunityVendorRating.tsx`
- `src/components/BrandLogo.tsx`
- `src/assets/photos/community-market.jpg`

The redesign introduces no database migrations, account changes, or worker rule
changes. No decorative rays, doodles, whisker marks, or generated market photos
are used.

## Photograph

`src/assets/photos/community-market.jpg` is “Market Stall Tents” by Connor Scott
McManus, downloaded from Pexels on November 24, 2026. It is general market imagery,
not evidence of a particular Raleigh venue or an endorsement.

- Source: https://www.pexels.com/photo/market-stall-tents-15807347/
- License: https://www.pexels.com/license/
- The source and photographer are recorded here. The Pexels license permits
  website use without an on-page credit; attribution is appreciated but not required.
