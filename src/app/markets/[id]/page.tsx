"use client";

import Link from "next/link";
import { organizerHref } from "../../../lib/marketOrganizers";
import { useParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { createClient } from "../../../lib/supabase/client";
import ReviewForm from "../../../components/ReviewForm";
import { getRatingColor } from "../../../lib/ratingColors";

import { formatAttendanceDate } from "../../../lib/attendanceDate";

import { selectReviews, reviewRangeError, type ReviewSort } from "../../../lib/reviewFilters";

type Market = {
  id: string;
  slug: string;
  name: string;
  city: string;
  state: string;
  description: string;
  is_sample: boolean;
  organizer: string | null;
};

type PublicReview = {
  attended_on: string | null;
  created_at?: string;
  id: string;
  market_id: string;
  booth_value: number;
  foot_traffic: number;
  organization: number;
  promotion: number;
  overall: number;
  vendor_categories: string[];
  other_category: string | null;
  booth_cost: number | null;
  booth_duration: "single" | "multi" | null;
  number_of_days: number | null;
  experience: string;
  would_return: string;
};

const ratingCategories = [
  { key: "overall", label: "Overall Experience", note: "Overall vendor satisfaction with the event." },
  { key: "booth_value", label: "Booth Value", note: "Was the booth fee worthwhile relative to sales, exposure, and return?" },
  { key: "foot_traffic", label: "Foot Traffic", note: "Vendor impressions of customer attendance, not an attendance count." },
  { key: "organization", label: "Event Organization", note: "Setup, communication, logistics, and event management." },
  { key: "promotion", label: "Event Promotion", note: "How effectively vendors felt the event was advertised." },
] as const;

const ratingLabels = ["Poor", "Below Average", "Average", "Good", "Exceptional"];
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

function median(values: number[]): number | null {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function range(values: number[]) {
  if (!values.length) return "Not reported";
  const low = Math.min(...values);
  const high = Math.max(...values);
  return low === high ? money.format(low) : `${money.format(low)} – ${money.format(high)}`;
}

function MarketReviews({ marketId }: { marketId: string }) {
  const [reviews, setReviews] = useState<PublicReview[]>([]);
  const [reviewSort, setReviewSort] = useState<ReviewSort>("attended-newest");
  const [attendedFrom, setAttendedFrom] = useState("");
  const [attendedTo, setAttendedTo] = useState("");
  const dateRangeError = reviewRangeError(attendedFrom, attendedTo);
  const visibleReviews = selectReviews(reviews, reviewSort, attendedFrom, attendedTo);
  function resetReviewFilters() {
    setReviewSort("attended-newest"); setAttendedFrom(""); setAttendedTo("");
  }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [member, setMember] = useState(false);
  const [summary, setSummary] = useState<{ count: number; overall: number | null }>({ count: 0, overall: null });

  useEffect(() => {
    let active = true;
    let generation = 0;
    const supabase = createClient();

    async function loadReviews() {
      const current = ++generation;
      const isCurrent = () => active && current === generation;
      if (!active) return;
      setLoading(true);
      setError("");
      setReviews([]);
      setMember(false);
      try {
        const { data: summaryData, error: summaryError } = await supabase.rpc("get_market_summary", { p_market_id: marketId });
        if (summaryError) throw summaryError;
        const row = summaryData?.[0];
        if (!row) throw new Error("Market summary was not returned.");
        if (!isCurrent()) return;
        setSummary({ count: Number(row.review_count), overall: row.overall_rating === null ? null : Number(row.overall_rating) });

        const { data: auth, error: authError } = await supabase.auth.getUser();
        if (!isCurrent()) return;
        if (authError && authError.name !== "AuthSessionMissingError") throw authError;
        if (!auth.user) return;

        const { data, error: reviewError } = await supabase.rpc("btb_market_reviews_with_attendance", { p_market_id: marketId });
        if (reviewError) throw reviewError;
        if (isCurrent()) {
          setReviews((data ?? []) as PublicReview[]);
          setMember(true);
        }
      } catch (cause) {
        console.error("Unable to load market reviews:", cause);
        if (isCurrent()) setError("We couldn't load the vendor report. Please refresh to try again.");
      } finally {
        if (isCurrent()) setLoading(false);
      }
    }

    void loadReviews();
    let refreshTimer: ReturnType<typeof setTimeout> | undefined;
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event !== "SIGNED_IN" && event !== "SIGNED_OUT") return;
      // Clear detailed content immediately when the account changes.
      generation++;
      setReviews([]);
      setMember(false);
      setLoading(true);
      clearTimeout(refreshTimer);
      refreshTimer = setTimeout(() => { void loadReviews(); }, 0);
    });
    return () => {
      active = false;
      generation++;
      clearTimeout(refreshTimer);
      subscription.unsubscribe();
    };
  }, [marketId]);

  const hasData = !loading && !error;
  const count = reviews.length;
  const averageRatings = ratingCategories.map((category) => {
    const values = reviews.map((review) => review[category.key]).filter((value) => Number.isFinite(value) && value >= 1 && value <= 5);
    return {
      ...category,
      count: values.length,
      average: values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null,
    };
  });

  const overallRating = averageRatings.find((category) => category.key === "overall")!;

  const returnCounts = ["Yes", "No", "Maybe"].map((answer) => ({
    answer,
    count: reviews.filter((review) => review.would_return === answer).length,
  }));
  const returnTotal = returnCounts.reduce((sum, item) => sum + item.count, 0);

  const feeReports = reviews.filter((review) => review.booth_cost !== null && Number.isFinite(Number(review.booth_cost)) && Number(review.booth_cost) >= 0);
  const dailyCosts = feeReports.flatMap((review) => {
    const duration = review.booth_duration === "single" ? 1 : review.booth_duration === "multi" ? review.number_of_days : null;
    return duration !== null && Number.isInteger(duration) && duration > 0
      ? [Number(review.booth_cost) / duration]
      : [];
  });
  const medianDaily = median(dailyCosts);
  const feeGroups = [
    { label: "Single-day total fees", values: feeReports.filter((review) => review.booth_duration === "single").map((review) => Number(review.booth_cost)) },
    { label: "Multi-day total fees", values: feeReports.filter((review) => review.booth_duration === "multi").map((review) => Number(review.booth_cost)) },
    { label: "Total fees; duration not provided", values: feeReports.filter((review) => review.booth_duration === null).map((review) => Number(review.booth_cost)) },
  ];
  const categoryCounts = new Map<string, number>();
  reviews.forEach((review) => {
    new Set(review.vendor_categories).forEach((category) => {
      categoryCounts.set(category, (categoryCounts.get(category) ?? 0) + 1);
    });
  });
  const categoryEntries = [...categoryCounts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const categorizedReviews = reviews.filter((review) => review.vendor_categories.length > 0).length;

  if (hasData && !member) {
    return (
      <section className="mt-16" aria-labelledby="public-verdict-heading">
        <p className="heritage-label">At a Glance</p>
        <div className="mt-4 flex flex-wrap items-end justify-between gap-5">
          <h2 id="public-verdict-heading" className="heritage-heading text-3xl md:text-4xl">The Vendor Verdict</h2>
          <span className="border border-[#252521]/20 px-4 py-2 text-xs font-bold uppercase tracking-wider text-[#626C57]">{summary.count} Approved {summary.count === 1 ? "Review" : "Reviews"}</span>
        </div>
            <div className="mt-6 border border-[#07472B] bg-[#07472B] px-6 py-6 text-[#F4F0E6] sm:px-8 sm:py-7">
              <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between sm:gap-8">
                <div className="max-w-xl">
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#D6D4BF]">Overall Experience</p>
                  <h3 className="mt-2 font-serif text-2xl font-bold sm:text-3xl">The big picture, from vendors.</h3>
                  <p className="mt-2 text-sm leading-relaxed text-[#D6D4BF]">{"Overall vendor satisfaction with the event."}</p>
                  <p className="mt-3 text-xs text-[#D6D4BF]">{summary.count} approved {summary.count === 1 ? "rating" : "ratings"} · {summary.count ? "Average overall experience" : "Awaiting vendor feedback"}</p>
                </div>
                <div className="shrink-0 sm:text-right">
                  <p className="rating-featured-score">{summary.overall === null ? <span className="text-2xl">Not rated yet</span> : <><span style={{ color: getRatingColor(summary.overall) }}>{summary.overall.toFixed(1)}</span><span className="ml-2 text-2xl font-normal text-[#626C57]">/ 5</span></>}</p>
                  <p className="mt-2 text-xs text-[#D6D4BF]">1 = Poor · 5 = Exceptional</p>
                </div>
              </div>
            </div>
        {summary.count > 0 && summary.count < 5 && <p className="mt-3 border-l-2 border-[#07472B] bg-[#E9E7DA] px-4 py-3 text-xs leading-relaxed text-[#55554E]">Early feedback: this score reflects {summary.count === 1 ? "one approved review" : `${summary.count} approved reviews`}. More vendor experiences will help build a fuller picture.</p>}
        <div className="rating-color-legend" aria-label="Rating scale from 1, poor, to 5, exceptional">
          <span>1 · Poor</span><span className="rating-color-ramp" aria-hidden="true" /><span>5 · Exceptional</span>
        </div>
        <div className="mt-4 border border-[#252521]/20 bg-[#E9E7DA] p-6 sm:p-8">
          <p className="heritage-label">Free Member Access</p>
          <h3 className="mt-3 font-serif text-2xl font-bold sm:text-3xl">See the full vendor report.</h3>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#55554E]">Create a free account to read approved vendor reviews, explore all five rating breakdowns, see reported booth costs, and find out whether vendors would return.</p>
          {summary.count === 0 && <p className="mt-3 text-sm text-[#55554E]">This market has no approved reviews yet. Detailed feedback will appear as reviews are published.</p>}
          <div className="mt-5 flex flex-wrap items-center gap-4">
            <Link href="/login" className="heritage-button">Sign In / Create Free Account →</Link>
            <span className="text-xs text-[#626C57]">Free to join · No review required to read</span>
          </div>
          <p className="mt-4 text-xs leading-relaxed text-[#626C57]">Vendor verification is required only when you want to submit a review. Public reviews do not display account names or email addresses.</p>
        </div>
      </section>
    );
  }

  return (
    <>
      <section className="mt-16" aria-labelledby="market-summary-heading">
        <p className="heritage-label">At a Glance</p>
        <div className="mt-4 flex flex-wrap items-end justify-between gap-5">
          <h2 id="market-summary-heading" className="heritage-heading text-3xl md:text-4xl">The Vendor Verdict</h2>
          {hasData && <span className="border border-[#252521]/20 px-4 py-2 text-xs font-bold uppercase tracking-wider text-[#626C57]">{count} Approved {count === 1 ? "Review" : "Reviews"}</span>}
        </div>
        <p className="mt-5 max-w-3xl text-sm leading-relaxed text-[#55554E]">A summary of the questions vendors answered: their ratings, whether they would return, reported booth costs, and the businesses represented.</p>
        <p className="mt-3 text-xs leading-relaxed text-[#626C57]">Only approved reviews contribute. Ratings use a 1–5 scale: Poor, Below Average, Average, Good, Exceptional. Optional answers may have fewer responses.</p>
        <div className="rating-color-legend" aria-label="Rating scale from 1, poor, to 5, exceptional">
          <span>1 · Poor</span><span className="rating-color-ramp" aria-hidden="true" /><span>5 · Exceptional</span>
        </div>

        {loading && <p className="mt-8 text-[#55554E]" role="status">Loading the vendor summary...</p>}
        {error && <p role="alert" className="mt-8 border-l-2 border-[#07472B] bg-[#E9E7DA] p-5 text-sm">{error}</p>}

        {hasData && (
          <>
            <div className="mt-6 border border-[#07472B] bg-[#07472B] px-6 py-6 text-[#F4F0E6] sm:px-8 sm:py-7">
              <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between sm:gap-8">
                <div className="max-w-xl">
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#D6D4BF]">Overall Experience</p>
                  <h3 className="mt-2 font-serif text-2xl font-bold sm:text-3xl">The big picture, from vendors.</h3>
                  <p className="mt-2 text-sm leading-relaxed text-[#D6D4BF]">{overallRating.note}</p>
                  <p className="mt-3 text-xs text-[#D6D4BF]">{overallRating.count} approved {overallRating.count === 1 ? "rating" : "ratings"} · {overallRating.count ? "Average overall experience" : "Awaiting vendor feedback"}</p>
                </div>
                <div className="shrink-0 sm:text-right">
                  <p className="rating-featured-score">{overallRating.average === null ? <span className="text-2xl">Not rated yet</span> : <><span style={{ color: getRatingColor(overallRating.average) }}>{overallRating.average.toFixed(1)}</span><span className="ml-2 text-2xl font-normal text-[#626C57]">/ 5</span></>}</p>
                  <p className="mt-2 text-xs text-[#D6D4BF]">1 = Poor · 5 = Exceptional</p>
                </div>
              </div>
            </div>
            {count > 0 && count < 5 && <p className="mt-3 border-l-2 border-[#07472B] bg-[#E9E7DA] px-4 py-3 text-xs leading-relaxed text-[#55554E]">Early feedback: this summary reflects {count === 1 ? "one approved review" : `${count} approved reviews`}. More vendor experiences will help build a fuller picture.</p>}
            <div className="mt-4 grid items-start gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {averageRatings.filter((category) => category.key !== "overall").map((category) => (
                <div key={category.key} className="border border-[#252521]/20 p-4 sm:p-5">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#07472B]">{category.label}</h3>
                    <p className="shrink-0 font-serif text-2xl font-bold">{category.average === null ? <span className="font-sans text-xs font-normal text-[#626C57]">Not rated yet</span> : <><span style={{ color: getRatingColor(category.average) }}>{category.average.toFixed(1)}</span> <span className="text-base text-[#626C57]">/ 5</span></>}</p>
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-[#55554E]">{category.note}</p>
                  <p className="mt-2 text-[11px] text-[#626C57]">{category.count} {category.count === 1 ? "rating" : "ratings"}{category.count > 0 ? " · Average score" : ""}</p>
                </div>
              ))}
              <div className="border border-[#252521]/20 p-4 sm:col-span-2 sm:p-5 lg:col-span-4">
                <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] sm:items-center">
                <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 sm:pr-5">
                  <h3 className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#07472B]">Would Vendors Return?</h3>
                  <p className="font-serif text-xl font-bold">{returnTotal ? `${Math.round(returnCounts[0].count / returnTotal * 100)}% yes` : "No answers yet"}</p>
                </div>
                <dl className="grid grid-cols-3 divide-x divide-[#252521]/15">
                  {returnCounts.map((item, index) => <div key={item.answer} className={index === 0 ? "pr-2 text-xs" : "px-2 text-xs"}><dt className="text-[#55554E]">{item.answer}</dt><dd className="mt-1 font-semibold">{item.count}{returnTotal > 0 ? ` · ${Math.round(item.count / returnTotal * 100)}%` : ""}</dd></div>)}
                </dl>
                </div>
                <p className="mt-2 text-[11px] text-[#626C57]">{returnTotal} {returnTotal === 1 ? "response" : "responses"} · Maybe is shown separately.</p>
              </div>
            </div>

            <div className="mt-3 grid items-start gap-3 lg:grid-cols-2">
              <div className="border border-[#252521]/20 p-4 sm:p-5">
                <h3 className="heritage-label">Reported Booth Costs</h3>
                <p className="mt-3 font-serif text-2xl font-bold">{medianDaily === null ? "No daily estimate yet" : `${money.format(medianDaily)} / day`}</p>
                <p className="mt-2 text-xs leading-relaxed text-[#55554E]">{medianDaily === null ? "A daily estimate needs both a reported fee and a known number of days." : "Median daily equivalent: each vendor’s total fee divided by the number of days it covered."}</p>
                {dailyCosts.length > 0 && <p className="mt-2 text-xs text-[#55554E]">Daily range: {range(dailyCosts)} · {dailyCosts.length} {dailyCosts.length === 1 ? "report" : "reports"}</p>}
                <dl className="mt-3 divide-y divide-[#252521]/15 border-y border-[#252521]/15">
                  {feeGroups.map((group) => <div key={group.label} className="py-2"><dt className="text-xs font-semibold">{group.label}</dt><dd className="mt-1 text-xs text-[#55554E]">{range(group.values)} <span className="text-[#626C57]">· {group.values.length} {group.values.length === 1 ? "report" : "reports"}</span></dd></div>)}
                </dl>
                <p className="mt-3 text-[11px] leading-relaxed text-[#626C57]">{feeReports.length} of {count} reviews include a booth fee. Zero-dollar fees are included. Fees are optional vendor reports, not organizer quotes. Multi-day totals may cover different lengths of time; reports without a known duration are excluded from daily estimates.</p>
              </div>
              <div className="border border-[#252521]/20 p-4 sm:p-5">
                <h3 className="heritage-label">Vendor Perspectives</h3>
                <p className="mt-3 text-xs leading-relaxed text-[#55554E]">The business categories represented in these reviews can help you judge how closely the feedback relates to what you sell.</p>
                {categoryEntries.length ? <dl className="mt-3 divide-y divide-[#252521]/15">{categoryEntries.map(([category, total]) => <div key={category} className="flex justify-between gap-4 py-2 text-xs"><dt>{category}</dt><dd className="shrink-0 font-semibold">{total} {total === 1 ? "review" : "reviews"}</dd></div>)}</dl> : <p className="mt-3 font-serif text-xl font-bold">No categories reported yet.</p>}
                <p className="mt-3 text-[11px] leading-relaxed text-[#626C57]">{categorizedReviews} of {count} reviewers shared categories. Vendors may select more than one, so category counts can exceed the number of reviews.</p>
              </div>
            </div>
          </>
        )}
      </section>

      <section id="vendor-reviews" className="mt-20 scroll-mt-8 border-t border-[#252521]/25 pt-14">
        <p className="heritage-label">From Behind the Booth</p>
        <h2 className="heritage-heading mt-4 text-4xl">Vendor Reviews</h2>
        <p className="mt-5 max-w-3xl text-sm leading-relaxed text-[#55554E]">Reviews are moderated before publication. Account names, emails, and private verification details are not displayed. Ratings reflect individual vendor experiences.</p>
        {hasData && count > 0 && <div className="mt-8 border border-[#252521]/20 bg-[#FFFCF6] p-5 sm:p-6">
          <div className="grid gap-5 md:grid-cols-3">
            <div className="min-w-0">
              <label htmlFor="review-sort" className="mb-2 block text-xs font-bold uppercase tracking-wider text-[#626C57]">Sort reviews</label>
              <select id="review-sort" value={reviewSort} onChange={event => setReviewSort(event.target.value as ReviewSort)} className="w-full min-w-0 border border-[#252521]/30 bg-[#FFFCF6] px-3 py-3 text-sm focus:outline-2 focus:outline-[#07472B]">
                <option value="attended-newest">Attendance date: newest first</option>
                <option value="attended-oldest">Attendance date: oldest first</option>
                <option value="rating-highest">Overall rating: highest first</option>
                <option value="rating-lowest">Overall rating: lowest first</option>
              </select>
            </div>
            <div className="min-w-0">
              <label htmlFor="reviews-from" className="mb-2 block text-xs font-bold uppercase tracking-wider text-[#626C57]">Attended from</label>
              <input id="reviews-from" type="date" min="0001-01-01" value={attendedFrom} onChange={event => setAttendedFrom(event.target.value)} aria-describedby="review-filter-help review-filter-status" aria-invalid={Boolean(dateRangeError)} className="w-full min-w-0 border border-[#252521]/30 bg-[#FFFCF6] px-3 py-3 text-sm focus:outline-2 focus:outline-[#07472B]" />
            </div>
            <div className="min-w-0">
              <label htmlFor="reviews-to" className="mb-2 block text-xs font-bold uppercase tracking-wider text-[#626C57]">Attended through</label>
              <input id="reviews-to" type="date" min="0001-01-01" value={attendedTo} onChange={event => setAttendedTo(event.target.value)} aria-describedby="review-filter-help review-filter-status" aria-invalid={Boolean(dateRangeError)} className="w-full min-w-0 border border-[#252521]/30 bg-[#FFFCF6] px-3 py-3 text-sm focus:outline-2 focus:outline-[#07472B]" />
            </div>
          </div>
          <p id="review-filter-help" className="mt-4 text-xs leading-relaxed text-[#626C57]">Filter by the date vendors attended, including both end dates. To see one market day, use the same date in both fields. Older reviews without an attendance date appear only when no date filter is set.</p>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p id="review-filter-status" role="status" aria-live="polite" className="text-sm text-[#55554E]">{dateRangeError || `Showing ${visibleReviews.length} of ${count} approved ${count === 1 ? "review" : "reviews"}.`}</p>
            {(attendedFrom || attendedTo || reviewSort !== "attended-newest") && <button type="button" onClick={resetReviewFilters} className="min-h-11 px-2 text-sm font-semibold text-[#07472B] underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07472B]">Reset review filters</button>}
          </div>
          <p className="mt-3 text-xs text-[#626C57]">Market scores and report summaries above use all approved reviews.</p>
        </div>}
        {hasData && count > 0 && !dateRangeError && visibleReviews.length === 0 && <div className="mt-8 border border-[#252521]/20 bg-[#E9E7DA] p-8 text-center">
          <h3 className="font-serif text-2xl font-bold">No reviews for these dates.</h3>
          <p className="mt-3 text-sm text-[#55554E]">Try a wider attendance-date range or reset the filters.</p>
          <button type="button" onClick={resetReviewFilters} className="mt-4 min-h-11 px-3 font-semibold text-[#07472B] underline underline-offset-4">Show all reviews</button>
        </div>}
        {loading && <p className="mt-8 text-[#55554E]" role="status">Loading approved reviews...</p>}
        {error && <p className="mt-8 text-sm text-[#07472B]">Reviews are unavailable. Please refresh to try again.</p>}
        {hasData && !count && <div className="mt-10 border border-[#252521]/20 bg-[#E9E7DA] px-8 py-14 text-center"><h3 className="font-serif text-3xl font-bold">Every vendor has a story.</h3><p className="mx-auto mt-5 max-w-xl leading-relaxed text-[#55554E]">No approved reviews have been published for this market yet. Pending submissions remain private.</p></div>}
        <div className="mt-10 space-y-6">
          {visibleReviews.map((review) => {
            const days = review.booth_duration === "single" ? 1 : review.booth_duration === "multi" ? review.number_of_days : null;
            const dailyCost = review.booth_cost !== null && days !== null && days > 0 ? Number(review.booth_cost) / days : null;
            return (
              <article key={review.id} className="heritage-card">
                <div className="flex flex-wrap items-center justify-between gap-4"><h3 className="font-serif text-2xl font-bold">Anonymous Vendor</h3><span className="text-sm font-bold" style={{ color: getRatingColor(review.overall) }}>Overall: {review.overall}/5 · {ratingLabels[review.overall - 1]}</span></div>
                <p className="mt-4 text-sm font-semibold text-[#626C57]">{review.attended_on ? <>Attended: <time dateTime={review.attended_on}>{formatAttendanceDate(review.attended_on)}</time></> : "Attendance date not provided"}</p>
                {review.vendor_categories.length > 0 && <div className="mt-5 flex flex-wrap gap-2">{review.vendor_categories.map((category) => <span key={category} className="border border-[#D6D4BF] bg-[#E9E7DA] px-3 py-2 text-xs text-[#55554E]">{category === "Other" && review.other_category ? `Other: ${review.other_category}` : category}</span>)}</div>}
                <dl className="mt-7 grid gap-4 border-y border-[#252521]/15 py-5 sm:grid-cols-2 lg:grid-cols-3">{ratingCategories.map(({ key, label }) => <div key={key}><dt className="text-xs font-semibold text-[#626C57]">{label}</dt><dd className="mt-1 text-sm font-bold" style={{ color: getRatingColor(review[key]) }}>{review[key]}/5 · {ratingLabels[review[key] - 1]}</dd></div>)}</dl>
                <p className="mt-7 whitespace-pre-wrap break-words leading-relaxed text-[#55554E]">{review.experience}</p>
                {(review.booth_cost !== null || review.booth_duration !== null) && <div className="mt-7 border-l-2 border-[#07472B] bg-[#E9E7DA] p-4 text-sm text-[#55554E]"><p className="font-semibold">Vendor-Reported Booth Information</p>{review.booth_cost !== null && <p className="mt-2">Total booth cost: {money.format(Number(review.booth_cost))}</p>}{review.booth_duration !== null && <p className="mt-2">Duration: {review.booth_duration === "single" ? "Single day" : review.number_of_days !== null ? `${review.number_of_days} days` : "Multi-day; number of days not provided"}</p>}{dailyCost !== null && <p className="mt-2">Estimated cost per day: {money.format(dailyCost)}</p>}</div>}
                <p className="mt-6 text-sm"><strong>Would participate again:</strong> {review.would_return}</p>
              </article>
            );
          })}
        </div>
      </section>
    </>
  );
}

function MarketProfileContent() {
  const { id } = useParams<{ id: string }>();
  const [market, setMarket] = useState<Market | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function loadMarket() {
      setLoading(true);
      setError("");
      setMarket(null);
      try {
        const supabase = createClient();
        const { data, error } = await supabase.from("markets").select("id, slug, name, city, state, description, is_sample, organizer").eq("slug", id).maybeSingle();
        if (error) throw error;
        if (active) setMarket(data);
      } catch (cause) {
        console.error("Unable to load market:", cause);
        if (active) setError("We couldn't load this market. Please refresh to try again.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadMarket();
    return () => { active = false; };
  }, [id]);

  return (
    <main className="flex-1 bg-[#F4F0E6] text-[#252521]">
      
      
      <section className="mx-auto max-w-6xl px-6 pb-20 pt-16">
        <Link href="/markets" className="text-sm font-semibold text-[#07472B] hover:underline">← Back to Market Directory</Link>
        {loading && <p className="mt-14 text-lg text-[#55554E]" role="status">Loading market profile...</p>}
        {!loading && error && <div className="mt-14 border border-[#252521]/20 bg-[#E9E7DA] p-8" role="alert"><h1 className="font-serif text-3xl font-bold">Unable to load market</h1><p className="mt-4 text-[#55554E]">{error}</p></div>}
        {!loading && !error && !market && <div className="mt-14 border border-[#252521]/20 bg-[#E9E7DA] p-8"><h1 className="font-serif text-3xl font-bold">Market not found</h1><p className="mt-4 text-[#55554E]">We couldn&apos;t find a market at this address. Return to the directory to explore available listings.</p></div>}
        {!loading && !error && market && <><div className="mt-14 flex items-center gap-4"><span className="h-px w-12 bg-[#07472B]" /><p className="heritage-label">Market Field Report</p></div><h1 className="heritage-heading mt-7 max-w-5xl text-5xl md:text-7xl">{market.name}</h1><p className="mt-6 text-sm font-bold uppercase tracking-[0.16em] text-[#626C57]">{market.city}, {market.state === "NC" ? "North Carolina" : market.state}{" · "}Market / Event</p>{market.organizer && <Link href={organizerHref(market.organizer)} className="mt-5 inline-block rounded-sm border border-[#07472B]/25 bg-[#E9E7DA] px-4 py-2 text-sm font-semibold text-[#07472B] hover:underline">Organized by {market.organizer} →</Link>}<p className="mt-8 max-w-3xl text-lg leading-relaxed text-[#55554E]">{market.description}</p>{market.is_sample && <div className="mt-12 border-l-2 border-[#07472B] bg-[#E9E7DA] px-6 py-5"><p className="text-sm leading-relaxed text-[#55554E]"><strong>Demonstration profile:</strong> This is a fictional event created to test Behind the Booth. It is not a real market. Reviews on this sample listing are test submissions.</p></div>}<MarketReviews key={`reviews-${market.id}`} marketId={market.id} /><ReviewForm key={`form-${market.id}`} marketId={market.id} /></>}
      </section>
      
    </main>
  );
}

export default function MarketProfile() {
  return <Suspense fallback={<main className="flex-1 bg-[#F4F0E6] p-12 text-[#252521]"><p role="status">Loading market profile...</p></main>}><MarketProfileContent /></Suspense>;
}
