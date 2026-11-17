
    
  
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createClient } from "../lib/supabase/client";
import { formatAttendanceDate, marketToday } from "../lib/attendanceDate";
import { opportunityDeadline } from "../lib/opportunityPresentation";
import { safeExternalUrl, statusLabel, type Opportunity } from "../lib/opportunities";

type Resource = { application_url: string; public_note: string; checked_on: string };
type Result = { marketId: string; resource: Resource | null; items: Opportunity[]; resourceError: boolean; opportunitiesError: boolean };
function eventDate(item: Opportunity) {
  return formatAttendanceDate(item.starts_on) + (item.ends_on !== item.starts_on ? ` – ${formatAttendanceDate(item.ends_on)}` : "");
}


export default function MarketParticipationPanel({ marketId, marketName, slug }: { marketId: string; marketName: string; slug: string }) {
  const [result, setResult] = useState<Result | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [expandedMarket, setExpandedMarket] = useState<string | null>(null);
  const showAll = expandedMarket === marketId;
  useEffect(() => {
    let active = true;
    const client = createClient();
    async function loadOpportunities() {
      let all: Opportunity[] = [];
      let offset = 0;
      while (true) {
        const { data, error } = await client.rpc("btb_public_opportunities", { p_market_id: marketId, p_offset: offset });
        if (error || !data || !Array.isArray(data.items)) throw new Error("Unable to load opportunities.");
        all = all.concat(data.items);
        offset += 100;
        if (!active || offset >= data.total || data.items.length === 0) break;
      }
      return all;
    }
    void (async () => {
      const [resourceResponse, opportunityResponse] = await Promise.allSettled([
        Promise.resolve(client.rpc("btb_market_vendor_application", { p_market_id: marketId })),
        loadOpportunities(),
      ]);
      if (!active) return;
      const resourceError = resourceResponse.status === "rejected" || Boolean(resourceResponse.value.error);
      const resource = resourceResponse.status === "fulfilled" && !resourceResponse.value.error ? resourceResponse.value.data as Resource | null : null;
      setResult({ marketId, resource, items: opportunityResponse.status === "fulfilled" ? opportunityResponse.value : [], resourceError, opportunitiesError: opportunityResponse.status === "rejected" });
    })();
    const timer = setInterval(() => { if (document.visibilityState === "visible") setRefresh(value => value + 1); }, 300000);
    return () => { active = false; clearInterval(timer); };
  }, [marketId, refresh]);

  const current = result?.marketId === marketId ? result : null;
  const resource = current?.resource;
  const applicationUrl = resource ? safeExternalUrl(resource.application_url) : null;
  const opportunities = (current?.items ?? []).filter(item => item.market_id === marketId && ["open", "limited"].includes(item.effective_status) && item.ends_on >= marketToday() && (!item.deadline || Date.parse(item.deadline) > Date.now())).sort((a,b) => a.starts_on.localeCompare(b.starts_on) || a.id.localeCompare(b.id));
  const report = applicationUrl ? `mailto:behindtheboothhq@gmail.com?subject=${encodeURIComponent(`Outdated vendor link: ${marketName}`)}&body=${encodeURIComponent(`Market: ${marketName}\nProfile: https://www.behindtheboothhq.com/markets/${slug}\nApplication information: ${applicationUrl}\n\nWhat needs updating:\n`)}` : "";
  return <section aria-label="Vendor applications and upcoming opportunities" className="mt-7 border border-[#252521]/20 bg-[#FFFCF6] px-5 py-4 sm:px-6">
    <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2">
      <h2 className="font-serif text-2xl font-bold">Vending at this market</h2>
    </div>
    <div className="mt-2 grid gap-4 border-t border-[#252521]/15 pt-4 md:grid-cols-2 md:gap-6">
      <div className="min-w-0">
        <p className="text-xs font-bold uppercase tracking-wider text-[#626C57]">General application</p>
        {!current ? <p role="status" className="mt-2 text-sm text-[#55554E]">Checking application information…</p> : applicationUrl && resource ? <>
          <a href={applicationUrl} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex min-h-11 items-center text-sm font-semibold text-[#07472B] underline underline-offset-4">Vendor application information ↗</a>
          <p className="text-xs text-[#626C57]">General / seasonal resource; openings vary.</p>
          <details className="mt-2 text-xs text-[#55554E]"><summary className="min-h-8 cursor-pointer py-2 font-semibold text-[#07472B]">Requirements & link details</summary>
            <div className="mt-1 space-y-3 border-l-2 border-[#07472B] pl-3 leading-relaxed">
              <p>This link explains how to apply; it does not confirm that applications or every vendor category are currently open.</p>
              {resource.public_note && <p className="whitespace-pre-wrap">{resource.public_note}</p>}
              <p>Link checked: <time dateTime={resource.checked_on}>{formatAttendanceDate(resource.checked_on)}</time>. Confirm current dates, fees, and eligibility with the organizer.</p>
              <a href={report} className="inline-flex min-h-9 items-center font-semibold text-[#07472B] underline">Report an outdated link</a>
            </div>
          </details>
        </> : <p className="mt-2 text-sm text-[#55554E]">{current.resourceError ? "Application information is temporarily unavailable." : "No verified general application link yet."}</p>}
      </div>
      <div className="min-w-0 border-t border-[#252521]/15 pt-4 md:border-l md:border-t-0 md:pl-6 md:pt-0">
        <p className="text-xs font-bold uppercase tracking-wider text-[#626C57]">Upcoming opportunities</p>
        {!current ? <p role="status" className="mt-2 text-sm text-[#55554E]">Checking upcoming dates…</p> : current.opportunitiesError ? <p className="mt-2 text-sm text-[#55554E]">Upcoming dates are temporarily unavailable.</p> : opportunities.length ? <>
          <p className="mt-2 text-sm font-semibold text-[#07472B]">{opportunities.length} upcoming {opportunities.length === 1 ? "date" : "dates"} · {opportunities.length === 1 ? statusLabel(opportunities[0].effective_status) : "Open or limited"}</p>
          <div className="mt-3 text-sm">
            <ul id={`market-dates-${marketId}`} className="mt-2 divide-y divide-[#252521]/15">{(showAll ? opportunities : opportunities.slice(0,3)).map(item => {const deadline=opportunityDeadline(item);return <li key={item.id} className="py-3 first:pt-1">
              <p className="text-sm font-semibold">{eventDate(item)}</p>
              <p className="mt-1 text-xs text-[#626C57]">{statusLabel(item.effective_status)} · {deadline.label}: {deadline.value}</p>
              {deadline.note&&<p className="mt-1 text-xs leading-relaxed text-[#626C57]">{deadline.note}</p>}
              <div className="mt-1 flex flex-wrap items-center gap-x-5">
                {safeExternalUrl(item.application_url) && <a href={safeExternalUrl(item.application_url)!} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center text-xs font-semibold text-[#07472B] underline">Official application ↗</a>}
                <Link href={`/opportunities#${item.id}`} className="inline-flex min-h-11 items-center text-xs font-semibold text-[#07472B] underline">Details & save →</Link>
              </div>
            </li>;})}</ul>
            <p className="mt-2 text-xs leading-relaxed text-[#626C57]">Acceptance and category availability are subject to organizer approval. Full fees, eligibility, sources, and saving are on the opportunity listing.</p>
            {opportunities.length > 3 && <button type="button" aria-expanded={showAll} aria-controls={`market-dates-${marketId}`} onClick={() => setExpandedMarket(showAll ? null : marketId)} className="mt-2 inline-flex min-h-11 items-center text-xs font-semibold text-[#07472B] underline underline-offset-4">{showAll ? "Show fewer dates" : `Show more (${opportunities.length - 3} additional ${opportunities.length - 3 === 1 ? "date" : "dates"})`}</button>}
          </div>
        </> : <p className="mt-2 text-sm text-[#55554E]">No recently verified open dates listed.</p>}
      </div>
    </div>
    {current && (current.resourceError || current.opportunitiesError) && <button type="button" onClick={() => setRefresh(value => value + 1)} className="mt-3 min-h-11 text-sm font-semibold text-[#07472B] underline">Retry application information</button>}
  </section>;
}

