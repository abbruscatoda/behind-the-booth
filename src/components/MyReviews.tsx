"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createClient } from "../lib/supabase/client";
import { formatAttendanceDate } from "../lib/attendanceDate";

type Review = { id: string; market_name: string | null; market_slug: string | null; status: string; attended_on: string | null; overall: number; experience: string; created_at: string };
type Result = { items: Review[]; total: number };

export default function MyReviews() {
  const [data, setData] = useState<Result>({ items: [], total: 0 });
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setLoading(true); setError(""); setData({ items: [], total: 0 });
    void (async () => {
      try {
        const { data, error } = await createClient().rpc("btb_my_reviews", { p_offset: offset });
        if (error) throw error;
        if (active) setData(data as Result);
      } catch {
        if (active) setError("We couldn't load your reviews. Please try refreshing your reviews.");
      } finally { if (active) setLoading(false); }
    })();
    return () => { active = false; };
  }, [offset, refresh]);
  return <section className="border border-[#252521]/20 bg-[#FFFCF6] p-5 sm:p-6" aria-labelledby="my-reviews-heading">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h2 id="my-reviews-heading" className="font-serif text-2xl font-bold">My Reviews</h2>
      <button type="button" disabled={loading} onClick={() => setRefresh(value => value + 1)} className="min-h-11 text-sm font-semibold text-[#07472B] underline underline-offset-4 disabled:opacity-50">Refresh reviews</button>
    </div>
    <p className="mt-3 text-sm leading-relaxed text-[#55554E]">Track your submissions here. Only approved reviews appear in market reports; your account name and email are not shown with public reviews.</p>
    {loading ? <p className="mt-5 text-sm" role="status">Loading your reviews...</p> : error ? <p role="alert" className="mt-5 text-sm text-[#07472B]">{error}</p> : <>
      <p role="status" className="mt-5 text-xs text-[#626C57]">{data.total === 0 ? "You haven't submitted any reviews yet." : `Showing ${data.items.length ? offset + 1 : 0}–${offset + data.items.length} of ${data.total} reviews.`}</p>
      {data.total === 0 && <Link href="/markets" className="mt-4 inline-block font-semibold text-[#07472B] underline">Find a market to review →</Link>}
      <div className="mt-4 space-y-4">{data.items.map(review => <article key={review.id} className="border border-[#252521]/20 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3"><h3 className="font-serif text-xl font-bold">{review.market_name ?? "Market no longer available"}</h3><span className="border border-[#07472B]/25 bg-[#E9E7DA] px-3 py-1 text-xs font-bold text-[#07472B]">{review.status === "approved" ? "Approved" : review.status === "pending" ? "Pending review" : "Not approved"}</span></div>
        <p className="mt-3 text-sm text-[#626C57]">{review.attended_on ? `Attended: ${formatAttendanceDate(review.attended_on)}` : "Attendance date not provided"}</p>
        <p className="mt-2 text-xs text-[#626C57]">Submitted: {new Date(review.created_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "America/New_York" })} · Overall: {review.overall}/5</p>
        <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-relaxed">{review.experience}</p>
        <p className="mt-3 text-xs leading-relaxed text-[#626C57]">{review.status === "approved" ? "Published in the market's member report." : review.status === "pending" ? "Waiting for moderation. Your review is not public yet." : "Not published. Editing and resubmission are not available yet. Contact us if you have a question."}</p>
        <div className="mt-4 flex flex-wrap gap-5">{review.market_slug && <Link href={`/markets/${encodeURIComponent(review.market_slug)}#vendor-reviews`} className="text-sm font-semibold text-[#07472B] underline">{review.status === "approved" ? "View market reviews" : "View market"} →</Link>}{review.status === "rejected" && <Link href="/contact" className="text-sm font-semibold text-[#07472B] underline">Contact us →</Link>}</div>
      </article>)}</div>
      {data.total > 20 && <div className="mt-5 flex items-center justify-between gap-4"><button type="button" disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - 20))} className="min-h-11 text-sm font-semibold text-[#07472B] underline disabled:opacity-40">Previous</button><button type="button" disabled={offset + 20 >= data.total} onClick={() => setOffset(value => value + 20)} className="min-h-11 text-sm font-semibold text-[#07472B] underline disabled:opacity-40">Next</button></div>}
    </>}
  </section>;
}
