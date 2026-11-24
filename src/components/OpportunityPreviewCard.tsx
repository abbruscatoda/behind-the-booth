import Link from "next/link";
import OpportunityVendorRating from "./OpportunityVendorRating";
import { formatAttendanceDate } from "../lib/attendanceDate";
import { opportunityBoothPrice } from "../lib/opportunityPresentation";
import { isNewlyPosted } from "../lib/opportunityRecency";
import { statusLabel, type Opportunity } from "../lib/opportunities";
import { hasVendorRating } from "../lib/ratingColors";

/** Public summaries are also redacted by the database, not merely hidden here. */
export default function OpportunityPreviewCard({item,joinHref}:{item:Opportunity;joinHref:string}) {
  const booth = opportunityBoothPrice(item);
  const priceNote = booth.note.length>130 ? "Pricing depends on the option and eligibility. See full details." : booth.note;
  const rolling = item.schedule_type === "rolling_market";
  const program = item.schedule_type === "seasonal_application" || item.schedule_type === "recurring_season";
  return <article id={item.id} className="heritage-card opportunity-card flex min-w-0 scroll-mt-8 flex-col [overflow-wrap:anywhere]">
    <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-semibold text-[#07472B]">
      <span>{statusLabel(item.effective_status)}</span>
      {isNewlyPosted(item) && <span className="border border-[#AD573B]/35 px-1.5 py-0.5 text-[#7A3A29]">New</span>}
    </div>
    <h2 className="mt-2 font-serif text-[1.375rem] font-bold leading-[1.15]"><Link href={`/markets/${item.market_slug}`} className="hover:underline">{item.title.replace(/\s*[—–-]\s*Rolling Vendor Applications$/i, "")}</Link></h2>
    {item.organizer && <p className="mt-1 text-xs font-semibold leading-snug text-[#07472B]">{item.organizer}</p>}
    <p className="mt-1 text-[13px] leading-snug text-[#55554E]">{item.city}, {item.state}</p>
    {hasVendorRating(item.history.review_count,item.history.overall)&&<OpportunityVendorRating score={item.history.overall} reviewCount={item.history.review_count} marketSlug={item.market_slug} marketTitle={item.title} />}
    <div className="my-2 border-y border-[#252521]/15 py-2 text-sm leading-snug">
      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#626C57]">{rolling ? "Ongoing market" : program ? "Application / program season" : "Market dates"}</p>
      <p className="mt-0.5 font-semibold">{rolling ? "Rolling vendor applications" : formatAttendanceDate(item.starts_on) + (item.ends_on !== item.starts_on ? ` – ${formatAttendanceDate(item.ends_on)}` : "")}</p>
      {item.effective_status==="announced"&&item.opens_on&&<p className="mt-1 text-xs font-semibold text-[#07472B]">Applications open {formatAttendanceDate(item.opens_on)}</p>}
      {program && <p className="mt-1 text-xs text-[#626C57]">Individual dates and booths require organizer approval.</p>}
      <p className="mt-2 text-[11px] text-[#626C57]">{booth.label}</p>
      <p className="mt-0.5 text-base font-bold">{booth.value}</p>
      {priceNote && <p className="mt-1 text-xs text-[#55554E]">{priceNote}</p>}
    </div>
    <p className="text-[13px] leading-snug text-[#55554E]">See application deadlines, fee details, category requirements, and the official application with a free account.</p>
    <Link href={joinHref} className="heritage-button opportunity-application mt-3 min-h-11 text-center">Unlock full details</Link>
    <p className="mt-1.5 text-center text-xs text-[#626C57]">Free membership · Access after signup</p>
  </article>;
}
