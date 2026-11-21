/** Publication recency is based on the first public posting, never a worker refresh. */
export type PublishedListing = { published_at?: string | null };

export const NEW_POSTED_DAYS = 7;
const DAY_MS = 24 * 60 * 60 * 1000;

export function firstPublishedTime(listing: PublishedListing): number | null {
  if (!listing.published_at) return null;
  const value = Date.parse(listing.published_at);
  return Number.isFinite(value) ? value : null;
}

export function isNewlyPosted(listing: PublishedListing, now = Date.now()): boolean {
  const time = firstPublishedTime(listing);
  return time !== null && time <= now && now - time < NEW_POSTED_DAYS * DAY_MS;
}

export function isPostedSince(
  listing: PublishedListing, lastVisit: string | null, now = Date.now(),
): boolean {
  if (!lastVisit) return false;
  const baseline = Date.parse(lastVisit);
  const published = firstPublishedTime(listing);
  return Number.isFinite(baseline) && baseline <= now
    && published !== null && published > baseline && published <= now;
}
