import Link from "next/link";
import { formatAttendanceDate } from "../lib/attendanceDate";
import { opportunityBoothPrice } from "../lib/opportunityPresentation";
import { isNewlyPosted } from "../lib/opportunityRecency";
import { statusLabel, type Opportunity } from "../lib/opportunities";

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
    <h2 className="mt-3 font-serif text-[1.45rem] font-bold leading-tight"><Link href={`/markets/${item.market_slug}`} className="hover:underline">{item.title.replace(/\s*[—–-]\s*Rolling Vendor Applications$/i, "")}</Link></h2>
    {item.organizer && <p className="mt-1.5 text-sm font-semibold text-[#07472B]">{item.organizer}</p>}
    <p className="mt-2 text-sm text-[#55554E]">{item.city}, {item.state}</p>
    <div className="my-3 border-y border-[#252521]/15 py-3 text-sm">
      <p className="text-[#626C57]">{rolling ? "Ongoing market" : program ? "Application / program season" : "Market dates"}</p>
      <p className="mt-1 font-semibold">{rolling ? "Rolling vendor applications" : formatAttendanceDate(item.starts_on) + (item.ends_on !== item.starts_on ? ` – ${formatAttendanceDate(item.ends_on)}` : "")}</p>
      {program && <p className="mt-1 text-xs text-[#626C57]">Individual dates and booths require organizer approval.</p>}
      <p className="mt-3 text-[#626C57]">{booth.label}</p>
      <p className="mt-1 text-base font-bold">{booth.value}</p>
      {priceNote && <p className="mt-1 text-xs text-[#55554E]">{priceNote}</p>}
    </div>
    <p className="mb-4 text-sm leading-relaxed text-[#55554E]">See application deadlines, fee details, category requirements, and the official application with a free account.</p>
    <Link href={joinHref} className="heritage-button mt-auto min-h-11 text-center">Unlock full details</Link>
    <p className="mt-2 text-center text-xs text-[#626C57]">Free membership · Access after signup</p>
  </article>;
}
