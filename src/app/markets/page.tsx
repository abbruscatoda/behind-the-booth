"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { organizerHref, organizerKey, organizerOptions } from "../../lib/marketOrganizers";
import { getRatingColor, getRatingDescriptor } from "../../lib/ratingColors";
import { createClient } from "../../lib/supabase/client";
import { hasNewReviews, latestReviewTime, type ReviewActivity, type ReviewWindow } from "../../lib/marketReviewRecency";
import { marketToday } from "../../lib/attendanceDate";

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

function MarketDirectory() {
  const params = useSearchParams();
  const router = useRouter();
  const organizer = params.get("organizer") ?? "";
  function selectOrganizer(value: string) {
    const next = new URLSearchParams(params.toString());
    if (value) next.set("organizer", value); else next.delete("organizer");
    router.replace(`/markets${next.size ? `?${next.toString()}` : ""}`, { scroll: false });
  }
  const [hasReviewsOnly, setHasReviewsOnly] = useState(false);
  const [hasUpcomingOnly, setHasUpcomingOnly] = useState(false);
  const [upcomingDates, setUpcomingDates] = useState<Record<string, string> | null>(null);
  const [checkingUpcoming, setCheckingUpcoming] = useState(true);
  const [upcomingRefresh, setUpcomingRefresh] = useState(0);
  const [today, setToday] = useState("");
  const [activity, setActivity] = useState<Record<string, ReviewActivity> | null>(null);
  const [reviewWindow, setReviewWindow] = useState<ReviewWindow>("all");
  const [sort, setSort] = useState("name");
  const [lastVisit, setLastVisit] = useState<string | null>(null);
  const [checkedAt, setCheckedAt] = useState(0);
  const [search, setSearch] = useState("");
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadMarkets() {
      try {
        const supabase = createClient();

        const requestStartedAt = Date.now();
        const [marketResponse, activityResponse] = await Promise.all([
          supabase.from("markets")
            .select("id, slug, name, city, state, description, is_sample, organizer")
            .eq("is_hidden", false).order("name"),
          Promise.resolve(supabase.rpc("btb_public_market_review_activity_v2"))
            .catch(() => ({ data: null, error: { message: "Review activity unavailable" } })),
        ]);
        const { data, error } = marketResponse;
        if (active && !activityResponse.error && Array.isArray(activityResponse.data)) {
          const rows = activityResponse.data as {market_id: string; review_count: number; overall_rating: number | null; latest_review_at: string | null}[];
          setActivity(Object.fromEntries(rows.map(row => [row.market_id, {
            count: Number(row.review_count), overall: row.overall_rating === null ? null : Number(row.overall_rating),
            latest: row.latest_review_at,
          }])));
          const now = Date.now();
          setCheckedAt(now);
          // Advance only after successful directory and activity loading. Keep
          // this tab's baseline stable across navigation and React remounts.
          if (!marketResponse.error) {
            try {
              const key = "btb_market_reviews_last_opened_v1";
              const sessionKey = "btb_market_reviews_session_baseline_v1";
              let previous = window.sessionStorage.getItem(sessionKey);
              if (previous === null) {
                previous = window.localStorage.getItem(key) ?? "";
                window.sessionStorage.setItem(sessionKey, previous);
              }
              const time = Date.parse(previous);
              setLastVisit(Number.isFinite(time) && time <= now ? previous : null);
              window.localStorage.setItem(key, new Date(requestStartedAt).toISOString());
            } catch { /* Directory browsing also works with storage disabled. */ }
          }
        }

        if (error) throw error;

        if (active) {
          setMarkets(data ?? []);
        }
      } catch (error) {
        console.error("Unable to load markets:", error);

        if (active) {
          setError(
            "We couldn't load the markets. Please refresh to try again."
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadMarkets();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    async function loadDates() {
      setCheckingUpcoming(true);
      try {
        const { data, error } = await createClient().rpc("btb_public_market_upcoming_dates");
        if (error || !Array.isArray(data)) throw error || new Error("Upcoming dates unavailable");
        if (active) {
          setUpcomingDates(Object.fromEntries(data.map((row: { market_id: string; last_event_ends_on: string }) => [row.market_id, row.last_event_ends_on])));
          setToday(marketToday());
        }
      } catch {
        if (active) setUpcomingDates(null);
      } finally { if (active) setCheckingUpcoming(false); }
    }
    void loadDates();
    // Expire past dates at North Carolina's midnight, including a tab left open.
    const updateDay = () => setToday(marketToday());
    const timer = setInterval(updateDay, 60_000);
    document.addEventListener("visibilitychange", updateDay);
    return () => { active = false; clearInterval(timer); document.removeEventListener("visibilitychange", updateDay); };
  }, [upcomingRefresh]);

  const organizers = organizerOptions(markets.map(market => market.organizer));
  const selectedOrganizer = organizers.find(name => organizerKey(name) === organizerKey(organizer)) ?? organizer;
  const filteredMarkets = markets.filter(market =>
    (!hasReviewsOnly || (activity?.[market.id]?.count ?? 0) > 0) &&
    (!hasUpcomingOnly || Boolean(upcomingDates?.[market.id] && upcomingDates[market.id] >= today)) &&
    (reviewWindow === "all" || hasNewReviews(activity?.[market.id], reviewWindow, lastVisit, checkedAt)) &&
    (!organizer || organizerKey(market.organizer) === organizerKey(organizer)) &&
    `${market.name} ${market.city} ${market.state} ${market.description} ${market.organizer ?? ""}`
      .toLowerCase().includes(search.trim().toLowerCase())
  ).sort((a, b) => sort === "reviews"
    ? (latestReviewTime(activity?.[b.id]) ?? 0) - (latestReviewTime(activity?.[a.id]) ?? 0) || a.name.localeCompare(b.name)
    : a.name.localeCompare(b.name));
  const weekCount = markets.filter(market => hasNewReviews(activity?.[market.id], "week", lastVisit, checkedAt)).length;
  const sinceCount = markets.filter(market => hasNewReviews(activity?.[market.id], "since", lastVisit, checkedAt)).length;
  const reviewOptions: {value: ReviewWindow; label: string}[] = [
    {value: "all", label: "All markets"},
    {value: "week", label: `New reviews this week (${weekCount})`},
    ...(lastVisit ? [{value: "since" as const, label: `New reviews since last visit (${sinceCount})`}] : []),
  ];
  const hasFilters = Boolean(search || organizer || hasReviewsOnly || hasUpcomingOnly || reviewWindow !== "all" || sort !== "name");
  const toggleClass = (selected: boolean) => `min-h-11 rounded-full border px-3 py-2 text-sm font-medium disabled:opacity-50 ${selected ? "border-[#07472B] bg-[#07472B] text-[#F4F0E6]" : "border-[#07472B]/20 bg-[#E8ECDD] text-[#07472B] hover:bg-[#DDE5D5]"}`;
  function clearFilters() { setSearch(""); selectOrganizer(""); setHasReviewsOnly(false); setHasUpcomingOnly(false); setReviewWindow("all"); setSort("name"); }

  return (
    <main className="directory-page flex-1 bg-[#F4F0E6] text-[#252521]">






      {/* Directory */}
      <section className="mx-auto max-w-6xl px-6 pb-16 pt-8 md:pt-10">
        <div className="mb-4 flex items-center gap-4">
          <p className="heritage-label directory-eyebrow">The Market Directory</p>
        </div>

        <h1 className="heritage-heading max-w-4xl text-4xl md:text-5xl">
          Find your next
          {" "}
          <span className="text-[#07472B]">great market.</span>
        </h1>

        <p className="mt-3 max-w-3xl text-base leading-relaxed text-[#55554E]">
          Explore markets, festivals, and pop-up events around Raleigh
          and the Triangle. Read vendor feedback before booking your booth.
        </p>

        {/* Search */}
        <div className="mt-6 border-y border-[#252521]/20 py-4">
          <div className="grid items-end gap-3 md:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)_minmax(10rem,0.65fr)]">
            <div className="min-w-0">
              <label
                htmlFor="market-search"
                className="mb-2 block text-xs font-bold uppercase tracking-[0.2em] text-[#626C57]"
              >
                Search the Directory
              </label>

              <input
                id="market-search"
                type="search"
                placeholder="Markets, cities, or organizers..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className="h-12 w-full min-w-0 border border-[#252521]/30 bg-[#FFFCF6] px-3 text-[#252521] outline-none transition placeholder:text-[#626C57] focus:border-[#07472B]"
              />
            </div>
            <div className="min-w-0"><label htmlFor="organizer-filter" className="mb-2 block text-xs font-bold uppercase tracking-[0.15em] text-[#626C57]">Filter by organizer</label>
              <select id="organizer-filter" value={selectedOrganizer} disabled={loading || Boolean(error)} onChange={event => selectOrganizer(event.target.value)} className="h-12 w-full min-w-0 border border-[#252521]/30 bg-[#FFFCF6] px-3 outline-none focus:border-[#07472B]">
                <option value="">All organizers</option>
                {organizer && !organizers.some(name => organizerKey(name) === organizerKey(organizer)) && <option value={organizer}>{organizer}</option>}
                {organizers.map(name => <option key={organizerKey(name)} value={name}>{name}</option>)}
              </select>
            </div>
            <div className="min-w-0"><label htmlFor="market-sort" className="mb-2 block text-xs font-bold uppercase tracking-[0.15em] text-[#626C57]">Sort markets</label>
              <select id="market-sort" value={sort} disabled={loading} onChange={event => setSort(event.target.value)} className="h-12 w-full min-w-0 border border-[#252521]/30 bg-[#FFFCF6] px-3 outline-none focus:border-[#07472B]">
                <option value="name">Market name</option><option value="reviews" disabled={activity === null}>Latest reviews</option>
              </select>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2" role="group" aria-label="Filter markets">
            <button type="button" aria-pressed={hasReviewsOnly} disabled={loading || activity === null} onClick={() => setHasReviewsOnly(value => !value)} className={toggleClass(hasReviewsOnly)}>Has reviews</button>
            <button type="button" aria-pressed={hasUpcomingOnly} aria-describedby="upcoming-events-help" disabled={loading || upcomingDates === null} onClick={() => setHasUpcomingOnly(value => !value)} className={toggleClass(hasUpcomingOnly)}>Has upcoming events</button>
          </div>
          <p id="upcoming-events-help" className="sr-only">Matches published event dates today or later, including multi-day events still in progress. General and seasonal application periods are excluded.</p>
          <div className="mt-2 flex flex-wrap items-center gap-2" role="group" aria-label="Filter by new review activity">
            {reviewOptions.map(option =>
              <button key={option.value} type="button" aria-pressed={reviewWindow === option.value} disabled={loading || activity === null} onClick={() => setReviewWindow(option.value)} className={toggleClass(reviewWindow === option.value)}>{option.label}</button>
            )}
            {hasFilters && <button type="button" onClick={clearFilters} className="min-h-11 px-3 py-2 text-sm font-semibold text-[#07472B] underline underline-offset-4">Clear filters</button>}
          </div>
          <p className="mt-2 text-xs leading-relaxed text-[#626C57]">New reviews are approved vendor feedback added in the last 7 days. Since last visit is specific to this browser.</p>
          <p
            className="mt-4 text-sm text-[#55554E]"
            role="status"
            aria-live="polite"
          >
            {loading
              ? "Loading markets..."
              : error
                ? error
                : `Showing ${filteredMarkets.length} ${
                    filteredMarkets.length === 1 ? "market" : "markets"
                  }.`}
          </p>
        </div>

        {!loading && !error && activity === null && <p role="status" className="mt-3 text-xs text-[#626C57]">Review counts are temporarily unavailable. You can still browse markets and open their profiles.</p>}
        {!loading && !error && upcomingDates === null && !checkingUpcoming && <p role="status" className="mt-3 text-xs text-[#626C57]">Upcoming-event dates are temporarily unavailable. <button type="button" onClick={() => setUpcomingRefresh(value => value + 1)} className="inline-flex min-h-11 items-center font-semibold text-[#07472B] underline">Retry upcoming dates</button></p>}
        <p className="mt-4 text-sm leading-relaxed text-[#55554E]">
          Can’t find the market you’re looking for?{" "}
          <Link
            href="/suggest-market"
            className="font-semibold text-[#07472B] underline underline-offset-4 hover:decoration-2 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#07472B]"
          >
            Suggest a market for us to add →
          </Link>
        </p>

        {/* Demo notice */}
        {markets.some(market => market.is_sample) && <div className="mt-10 border-l-2 border-[#07472B] bg-[#E9E7DA] px-5 py-4">
          <p className="text-sm leading-relaxed text-[#55554E]">
            <strong>Demonstration directory:</strong> Listings marked
            Demo are fictional examples used to test Behind the Booth.
            These are separate from real market listings.
          </p>
        </div>}

        {/* Market cards */}
        <div
          className="mt-4 grid items-start gap-4 md:grid-cols-2 lg:grid-cols-3"
          aria-busy={loading}
        >
          {filteredMarkets.map((market) => (
            <article
              key={market.id}
              className="heritage-card market-card flex min-w-0 flex-col [overflow-wrap:anywhere]"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#07472B]">Market / Event</span>

                <span className="text-xs font-semibold uppercase tracking-wider text-[#626C57]">
                  {market.is_sample ? "Demo" : "Listing"}
                </span>
              </div>

              <div className="my-2 h-px bg-[#252521]/20" />

              {(hasNewReviews(activity?.[market.id], "week", lastVisit, checkedAt) || hasNewReviews(activity?.[market.id], "since", lastVisit, checkedAt)) &&
                <span className="mb-1.5 self-start border border-[#07472B]/25 bg-[#E9E7DA] px-2 py-0.5 text-xs font-bold text-[#07472B]">{hasNewReviews(activity?.[market.id], "since", lastVisit, checkedAt) ? "New reviews since last visit" : "New reviews"}</span>}

              <h2 className="font-serif text-[1.625rem] font-bold leading-[1.15]">
                <Link href={`/markets/${market.slug}`} className="text-inherit hover:text-[#07472B] hover:underline underline-offset-4">{market.name}</Link>
              </h2>

              <p className="mt-1.5 text-xs font-semibold uppercase tracking-[0.04em] text-[#626C57]">
                {market.city},{" "}
                {market.state === "NC" ? "North Carolina" : market.state}
              </p>

              {market.organizer && <Link href={organizerHref(market.organizer)} className="mt-2 self-start rounded-sm border border-[#07472B]/25 bg-[#E9E7DA] px-2.5 py-2 text-xs font-semibold text-[#07472B] hover:underline">Organizer: {market.organizer}</Link>}

              {activity?.[market.id]?.count && activity[market.id].overall != null ? (
                <div className="market-rating mt-2 border-y border-[#252521]/15 py-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#55554E]">Overall vendor rating</p>
                  <div className="mt-0.5 flex flex-wrap items-center gap-x-2.5 gap-y-1">
                    <p className="shrink-0" style={{color: getRatingColor(activity[market.id].overall!)}}><span className="text-[1.75rem] font-bold leading-none tracking-tight">{activity[market.id].overall!.toFixed(1)}</span><span className="ml-0.5 text-sm font-semibold">/ 5</span></p>
                    <div className="min-w-0 flex-1">
                      <p className="text-[13px] font-bold leading-snug" style={{color: getRatingColor(activity[market.id].overall!)}} title="Rating scale: 1 Poor · 2 Below Average · 3 Average · 4 Good · 5 Exceptional">{getRatingDescriptor(activity[market.id].overall!)}</p>
                      <p className="mt-0.5 text-xs leading-snug text-[#55554E]">Based on {activity[market.id].count} vendor {activity[market.id].count === 1 ? "review" : "reviews"}</p>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="mt-2 text-xs font-semibold text-[#626C57]">{activity?.[market.id] ? "No reviews yet" : loading ? "Loading review activity…" : "Review activity unavailable"}</p>
              )}
              <p className="mt-2 text-sm leading-snug text-[#55554E]">
                {market.description}
              </p>

              <div className="mt-2 border-t border-[#252521]/20 pt-1">
                <Link
                  href={`/markets/${market.slug}`}
                  className="inline-flex min-h-11 items-center text-sm font-semibold text-[#07472B] hover:underline"
                >
                  View market details →
                </Link>
              </div>
            </article>
          ))}
        </div>

        {!loading && !error && filteredMarkets.length === 0 && (
          <div className="mt-10 border border-[#252521]/20 bg-[#E9E7DA] p-10 text-center">
            <h2 className="font-serif text-2xl font-bold">
              No markets found.
            </h2>
            <p className="mt-3 text-[#55554E]">
              {markets.length === 0
                ? "There are no market listings yet. Check back soon."
                : hasUpcomingOnly ? "No markets match upcoming event dates and your other filters. Try a different search or clear your filters."
                : reviewWindow !== "all" ? "No markets match this review window and your other filters. Try All markets or clear your filters." : "Try a different search or clear your filters."}
            </p>
            {hasFilters && <button type="button" onClick={clearFilters} className="mt-4 min-h-11 px-3 text-sm font-semibold text-[#07472B] underline">Clear filters</button>}
          </div>
        )}
      </section>



    </main>
  );
}

export default function MarketsPage() {
  return <Suspense fallback={<main className="mx-auto max-w-6xl px-6 py-20"><p role="status">Loading market directory…</p></main>}><MarketDirectory /></Suspense>;
}
