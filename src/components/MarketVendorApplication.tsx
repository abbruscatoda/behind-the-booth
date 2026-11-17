"use client";
import ExternalLinkIcon from "./ExternalLinkIcon";
import { useEffect, useState } from "react";
import { createClient } from "../lib/supabase/client";
import { safeExternalUrl } from "../lib/opportunities";
import { formatAttendanceDate } from "../lib/attendanceDate";

type Resource = { application_url: string; source_url: string; resource_kind: string; public_note: string; checked_on: string };
export default function MarketVendorApplication({ marketId, marketName, slug }: { marketId: string; marketName: string; slug: string }) {
  const [result, setResult] = useState<{ marketId: string; resource: Resource } | null>(null);
  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const { data, error } = await createClient().rpc("btb_market_vendor_application", { p_market_id: marketId });
        if (active) setResult(!error && data ? { marketId, resource: data } : null);
      } catch { if (active) setResult(null); }
    })();
    return () => { active = false; };
  }, [marketId]);
  if (!result || result.marketId !== marketId) return null;
  const resource = result.resource;
  const url = safeExternalUrl(resource.application_url);
  if (!url) return null;
  const report = `mailto:behindtheboothhq@gmail.com?subject=${encodeURIComponent(`Outdated vendor link: ${marketName}`)}&body=${encodeURIComponent(`Market: ${marketName}\nProfile: https://www.behindtheboothhq.com/markets/${slug}\nApplication information: ${url}\n\nWhat needs updating:\n`)}`;
  return <aside aria-label="Vendor application information" className="mt-8 max-w-3xl border-l-2 border-[#07472B] bg-[#E9E7DA] p-5 sm:p-6">
    <h2 className="font-serif text-xl font-bold">Interested in vending here?</h2>
    <p className="mt-3 text-sm leading-relaxed text-[#55554E]">Use the organizer’s general or seasonal vendor information to learn how to apply. This link does not confirm that applications or every vendor category are currently open.</p>
    {resource.public_note && <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-[#55554E]">{resource.public_note}</p>}
    <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-3">
      <a href={url} target="_blank" rel="noopener noreferrer" className="min-h-11 inline-flex items-center font-semibold text-[#07472B] underline underline-offset-4">Vendor application information <ExternalLinkIcon /></a>
      <a href={report} className="min-h-11 inline-flex items-center text-xs text-[#626C57] underline">Report an outdated link</a>
    </div>
    <p className="mt-3 text-xs text-[#626C57]">Link checked: <time dateTime={resource.checked_on}>{formatAttendanceDate(resource.checked_on)}</time>. Dates, fees, eligibility, and application windows may change.</p>
  </aside>;
}
