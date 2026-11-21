"use client";
import ExternalLinkIcon from "./ExternalLinkIcon";
import Link from "next/link";
import { categoryEvidenceLabel, categoryHighlights, activeCategoryEvidence, listedOpportunityCategories, opportunityCategoryStatus } from "../lib/opportunityCategories";
import { opportunityDeadline, opportunityBoothPrice } from "../lib/opportunityPresentation";
import { formatAttendanceDate } from "../lib/attendanceDate";
import { fee, safeExternalUrl, statusLabel, type Opportunity } from "../lib/opportunities";

/** Quick comparison card: verified facts first; detailed evidence lives in a modal. */
export default function OpportunityCard({
 item, categoryFilter, saved, saving, onSave, onViewDetails,
}:{
 item:Opportunity; categoryFilter:string; saved:boolean; saving:boolean;
 onSave:()=>void; onViewDetails:()=>void;
}) {
 const deadline=opportunityDeadline(item);
 const booth=opportunityBoothPrice(item);
 const listed=listedOpportunityCategories(item);
 const highlights=categoryHighlights(item);
 const evidence=activeCategoryEvidence(item);
 const selected=categoryFilter ? evidence[categoryFilter] : undefined;
 const categoryText=categoryFilter
   ? opportunityCategoryStatus(item,categoryFilter)==="eligible" ? `${categoryFilter} — listed by organizer` : `${categoryFilter} — unconfirmed`
   : listed.length ? `${listed.slice(0,3).join(", ")}${listed.length>3?` +${listed.length-3} more`:""}` : "Not confirmed for specific categories";
 const displayTitle=item.schedule_type==="rolling_market"
   ? item.title.replace(/\s*[—–-]\s*Rolling Vendor Applications$/i,"") : item.title;
 const isRolling=item.schedule_type==="rolling_market";
 const available=["open","limited","waitlist"].includes(item.effective_status);
 const applicationUrl=safeExternalUrl(item.application_url);
 const statusTone=item.effective_status==="open"
   ? "border-[#07472B]/25 bg-[#E9E7DA] text-[#07472B]"
   : item.effective_status==="limited" || item.effective_status==="waitlist"
     ? "border-[#AD573B]/30 bg-[#AD573B]/10 text-[#7A3A29]"
     : "border-[#252521]/20 bg-[#252521]/5 text-[#55554E]";
 return <article id={item.id} className="heritage-card flex h-full min-w-0 scroll-mt-8 flex-col [overflow-wrap:anywhere]">
   <div className="flex flex-wrap items-center justify-between gap-2">
     <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#626C57]">{isRolling?"Ongoing market":item.schedule_type==="seasonal_application"?"Seasonal application":item.schedule_type==="recurring_season"?"Seasonal waitlist":"Vendor opportunity"}</p>
     <span className={`rounded-sm border px-2 py-1 text-[11px] font-semibold leading-snug ${statusTone}`}>{statusLabel(item.effective_status)}</span>
   </div>
   <div className="mt-3 h-px bg-[#252521]/15" />
   <h2 className="mt-4 font-serif text-[1.45rem] font-bold leading-[1.13] tracking-[-0.015em]"><Link href={`/markets/${item.market_slug}`} className="text-inherit underline-offset-4 hover:text-[#07472B] hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07472B]">{displayTitle}</Link></h2>
   {item.organizer && item.organizer.toLocaleLowerCase()!==displayTitle.toLocaleLowerCase()&&<p className="mt-2 line-clamp-2 text-xs font-semibold text-[#07472B]">By {item.organizer}</p>}
   <p className="mt-2 text-sm font-medium text-[#55554E]">{item.city}, {item.state}</p>
   {item.venue && item.venue.toLocaleLowerCase()!==`${item.city}, ${item.state}`.toLocaleLowerCase()&&<p className="mt-1 line-clamp-2 text-xs leading-relaxed text-[#626C57]">{item.venue}</p>}
   <div className="mt-4 border-t border-[#252521]/15 pt-3">
     <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#626C57]">{isRolling?"When to apply":"Market dates"}</p>
     <p className="mt-1 text-sm font-semibold leading-snug">{isRolling?"Ongoing · rolling applications":formatAttendanceDate(item.starts_on)+(item.ends_on!==item.starts_on?" – "+formatAttendanceDate(item.ends_on):"")}</p>
     {!isRolling&&<p className="mt-2 text-xs leading-relaxed text-[#55554E]"><span className="font-semibold">{deadline.label}:</span> {deadline.value}</p>}
     {isRolling&&<p className="mt-1 text-xs text-[#626C57]">No individual date or booth is guaranteed.</p>}
   </div>
   <dl className="mt-4 grid grid-cols-2 gap-x-3 gap-y-2 border-y border-[#252521]/15 py-3">
     <div className="min-w-0"><dt className="text-[11px] font-medium text-[#626C57]">{booth.label}</dt><dd className="mt-1 text-base font-bold leading-tight text-[#252521]">{booth.value}</dd></div>
     <div className="min-w-0"><dt className="text-[11px] font-medium text-[#626C57]">Application fee</dt><dd className="mt-1 text-sm font-semibold leading-snug">{fee(item.application_fee)}</dd>{item.application_fee!==null&&/waived for current vendors/i.test(item.fee_notes)&&<p className="mt-1 text-[11px] leading-snug text-[#626C57]">Waived for current vendors</p>}</div>
     {item.deposit!==null&&<div className="col-span-2 text-xs text-[#55554E]">Deposit: <span className="font-semibold">{fee(item.deposit)}</span></div>}
     {booth.note&&<p className="col-span-2 text-xs text-[#07472B]">{booth.note}</p>}
   </dl>
   <p className="mt-3 text-xs leading-relaxed text-[#55554E]"><span className="font-semibold text-[#252521]">Vendor categories:</span> <span className="line-clamp-2">{categoryText}</span></p>
   {highlights.length>0&&<p className="mt-3 border-l-2 border-[#AD573B] pl-3 text-xs leading-relaxed text-[#55554E]"><strong>{highlights[0][0]}:</strong> {categoryEvidenceLabel(highlights[0][1])}{highlights.length>1?` · +${highlights.length-1} more notes`:""}</p>}
   {selected?.note&&!highlights.some(([category])=>category===categoryFilter)&&<p className="mt-2 line-clamp-2 text-xs leading-relaxed text-[#626C57]">{selected.note}</p>}
   <p className="mt-3 text-xs text-[#626C57]">{item.history.review_count>0?`${item.history.overall?.toFixed(1)??"—"}/5 · ${item.history.review_count} vendor ${item.history.review_count===1?"review":"reviews"}`:"No vendor reviews yet"}</p>
   <div className="mt-auto pt-5">
     {available&&applicationUrl
       ? <a href={applicationUrl} target="_blank" rel="noopener noreferrer" className="heritage-button min-h-11 w-full text-center">{item.effective_status==="waitlist"?"Official waitlist":"Official application"} <ExternalLinkIcon /></a>
       : <p className="flex min-h-11 items-center justify-center border border-[#252521]/20 bg-[#E9E7DA] px-3 py-2 text-center text-xs font-semibold text-[#626C57]">{item.effective_status==="closed"?"Application closed":"Application not currently verified"}</p>}
     <div className="mt-3 flex items-center justify-between gap-3 border-t border-[#252521]/15 pt-2">
       <button type="button" onClick={onViewDetails} aria-haspopup="dialog" className="min-h-11 text-left text-sm font-semibold text-[#07472B] underline underline-offset-4 hover:decoration-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07472B]">View full details</button>
       <button type="button" disabled={saving} onClick={onSave} aria-label={saved?`Remove ${item.title} from saved opportunities`:`Save ${item.title}`} className="min-h-11 shrink-0 text-right text-xs font-semibold text-[#07472B] underline underline-offset-4 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07472B]">{saved?"Saved ✓":"Save"}</button>
     </div>
   </div>
 </article>;
}
