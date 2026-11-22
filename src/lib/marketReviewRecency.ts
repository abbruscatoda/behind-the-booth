/** Only publicly approved review activity belongs in directory recency. */
export type ReviewActivity = { count: number; overall: number | null; latest: string | null };
export type ReviewWindow = "all" | "week" | "since";
export function latestReviewTime(activity?: ReviewActivity): number | null {
  const time = activity?.latest ? Date.parse(activity.latest) : NaN;
  return activity && activity.count > 0 && Number.isFinite(time) ? time : null;
}
export function hasNewReviews(activity: ReviewActivity | undefined, window: ReviewWindow, baseline: string | null, now: number): boolean {
  const latest = latestReviewTime(activity);
  if (latest === null || latest > now) return false;
  if (window === "week") return now - latest < 7 * 86400000;
  const since = baseline ? Date.parse(baseline) : NaN;
  return window === "since" && Number.isFinite(since) && since <= now && latest > since;
}
