export type ReviewSort = "attended-newest" | "attended-oldest" | "rating-highest" | "rating-lowest";
export type DatedReview = {
  id: string;
  attended_on: string | null;
  overall: number;
  created_at?: string;
};

export function isCalendarDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value < "0001-01-01") return false;
  const parsed = new Date(`${value}T12:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

export function reviewRangeError(from: string, to: string): string {
  if ((from && !isCalendarDate(from)) || (to && !isCalendarDate(to))) return "Enter a valid attendance date.";
  return from && to && from > to ? "The end date must be on or after the start date." : "";
}

export function selectReviews<T extends DatedReview>(reviews: readonly T[], sort: ReviewSort, from = "", to = ""): T[] {
  if (reviewRangeError(from, to)) return [];
  const date = (review: T) => review.attended_on && isCalendarDate(review.attended_on) ? review.attended_on : "";
  return reviews.filter(review => {
    if (!from && !to) return true;
    const attended = date(review);
    return Boolean(attended) && (!from || attended >= from) && (!to || attended <= to);
  }).sort((a, b) => {
    if (sort === "rating-highest" || sort === "rating-lowest") {
      const difference = sort === "rating-highest" ? b.overall - a.overall : a.overall - b.overall;
      if (difference) return difference;
    }
    const ad = date(a), bd = date(b);
    // Legacy undated reviews remain visible, always after dated reviews in date sorts.
    if (!ad && bd) return 1;
    if (ad && !bd) return -1;
    const dates = sort === "attended-oldest" ? ad.localeCompare(bd) : bd.localeCompare(ad);
    return dates || (b.created_at ?? "").localeCompare(a.created_at ?? "") || a.id.localeCompare(b.id);
  });
}
