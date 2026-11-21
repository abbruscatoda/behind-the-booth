"use client";
import ExternalLinkIcon from "./ExternalLinkIcon";
import Link from "next/link";
import { useEffect, useRef } from "react";
import { activeCategoryEvidence, categoryEvidenceLabel, categoryHighlights, listedOpportunityCategories } from "../lib/opportunityCategories";
import { currentCoverage, coverageLabels, coverageStatus } from "../lib/researchCoverage";
import { opportunityDeadline, opportunityBoothPrice, opportunityDetailSections } from "../lib/opportunityPresentation";
import { formatAttendanceDate } from "../lib/attendanceDate";
import { fee, safeExternalUrl, statusLabel, type Opportunity } from "../lib/opportunities";

/** A native modal allows in-depth research without changing neighboring card heights. */
export default function OpportunityDetailsDialog({item,onClose}:{item:Opportunity;onClose:()=>void}) {
 const dialogRef=useRef<HTMLDialogElement>(null);
 useEffect(()=>{
  const dialog=dialogRef.current;
  if(dialog && !dialog.open)dialog.showModal();
  return ()=>{if(dialog?.open)dialog.close();};
 },[]);
 const deadline=opportunityDeadline(item);
 const booth=opportunityBoothPrice(item);
 const detail=opportunityDetailSections(item);
 const deadlineNotes=[...new Set([deadline.note,...detail.notes].filter(Boolean))];
 const evidence=activeCategoryEvidence(item);
 const listed=listedOpportunityCategories(item);
 const highlights=categoryHighlights(item);
 const coverage=currentCoverage(item.research_coverage);
 const actionUrl=safeExternalUrl(item.application_url);
 const sourceUrl=safeExternalUrl(item.source_url);
 const available=["open","limited","waitlist"].includes(item.effective_status);
 return <dialog ref={dialogRef}
  aria-labelledby={`opportunity-dialog-title-${item.id}`}
  onClose={onClose}
  onClick={event=>{if(event.target===event.currentTarget)dialogRef.current?.close();}}
  className="m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-3xl overflow-y-auto rounded-sm border border-[#252521]/30 bg-[#FFFCF6] p-0 text-[#252521] shadow-2xl backdrop:bg-[#252521]/60"
 >
  <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-[#252521]/20 bg-[#FFFCF6] px-5 py-4 sm:px-7">
   <div className="min-w-0">
    <p className="heritage-label">Opportunity details</p>
    <h2 id={`opportunity-dialog-title-${item.id}`} className="mt-2 font-serif text-2xl font-bold leading-tight sm:text-3xl">{item.title}</h2>
    <p className="mt-1 text-sm text-[#626C57]">{item.city}, {item.state} · {statusLabel(item.effective_status)}</p>
   </div>
   <button type="button" onClick={()=>dialogRef.current?.close()} className="shrink-0 rounded-sm border border-[#252521]/25 px-3 py-2 text-sm font-semibold text-[#07472B] hover:bg-[#E9E7DA] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07472B]" aria-label="Close opportunity details">Close <span aria-hidden="true">×</span></button>
  </div>
  <div className="space-y-5 px-5 py-6 sm:px-7">
   <div className="grid gap-4 border-b border-[#252521]/15 pb-5 text-sm sm:grid-cols-2">
    <div><p className="text-xs font-semibold uppercase tracking-wide text-[#626C57]">Organizer</p><p className="mt-1 font-semibold">{item.organizer}</p><p className="mt-1 text-[#55554E]">{item.venue} · {item.city}, {item.state}</p></div>
    <div><p className="text-xs font-semibold uppercase tracking-wide text-[#626C57]">{item.schedule_type==="rolling_market"?"Application window":"Market dates"}</p>
     <p className="mt-1 font-semibold">{item.schedule_type==="rolling_market"?"Ongoing — rolling vendor applications":formatAttendanceDate(item.starts_on)+(item.ends_on!==item.starts_on?" – "+formatAttendanceDate(item.ends_on):"")}</p>
     <p className="mt-1"><strong>{deadline.label}:</strong> {deadline.value}</p>
    </div>
    <div><p className="text-xs font-semibold uppercase tracking-wide text-[#626C57]">{booth.label}</p><p className="mt-1 font-semibold">{booth.value}</p>{booth.note&&<p className="mt-1 text-xs">{booth.note}</p>}</div>
    <div><p className="text-xs font-semibold uppercase tracking-wide text-[#626C57]">Application fee</p><p className="mt-1 font-semibold">{fee(item.application_fee)}</p>{item.deposit!==null&&<p className="mt-1">Deposit: {fee(item.deposit)}</p>}</div>
   </div>
   {highlights.length>0&&<div className="border-l-2 border-[#AD573B] bg-[#F4F0E6] px-4 py-3">
    <h3 className="font-semibold">Important category notes</h3>
    <ul className="mt-2 list-disc space-y-2 pl-4 text-sm leading-relaxed">{highlights.map(([category,entry])=><li key={category}>
      <strong>{category}: {categoryEvidenceLabel(entry)}.</strong> {entry.note}
      {entry.application_deadline&&Number.isFinite(Date.parse(entry.application_deadline))&&<span> Separate deadline: {new Date(entry.application_deadline).toLocaleString("en-US",{timeZone:"America/New_York",month:"short",day:"numeric",year:"numeric",hour:"numeric",minute:"2-digit"})}.</span>}
      {entry.application_state&&safeExternalUrl(entry.source_url)&&<> <a href={safeExternalUrl(entry.source_url)!} target="_blank" rel="noopener noreferrer" className="font-semibold text-[#07472B] underline">View separate application <ExternalLinkIcon /></a></>}
    </li>)}</ul>
   </div>}
       <div className="space-y-4 pb-2 leading-relaxed text-[#55554E]">
         {deadlineNotes.length>0&&<div><h3 className="font-semibold text-[#252521]">Deadline notes</h3><ul className="mt-2 list-disc space-y-2 pl-5">{deadlineNotes.map(note=><li key={note}>{note}</li>)}</ul></div>}
         <div><h3 className="font-semibold text-[#252521]">Fee details</h3>
           <dl className="mt-2 space-y-1 text-xs">
             {item.application_fee===null&&<div><dt className="inline font-semibold">Application fee: </dt><dd className="inline">Not published</dd></div>}
             {item.deposit===null&&<div><dt className="inline font-semibold">Deposit: </dt><dd className="inline">Not published</dd></div>}
           </dl>
           {detail.fees.length>0&&<ul className="mt-2 list-disc space-y-2 pl-5">{detail.fees.map(note=><li key={note}>{note}</li>)}</ul>}
           <p className="mt-2 text-xs">{item.booth_fee===null||item.application_fee===null||item.deposit===null?"Some costs aren’t published. Confirm the total with the organizer.":"Confirm the total with the organizer, including required add-ons and processing fees."}</p>
         </div>
         <div className="text-sm"><Link href={`/markets/${item.market_slug}#vendor-reviews`} className="font-semibold text-[#07472B] underline">{item.history.review_count?"Read vendor reviews →":"View market & add a review →"}</Link>
           <p className="mt-1 text-xs text-[#626C57]">{item.history.review_count?`${item.history.overall}/5 · ${item.history.review_count} reviews from ${item.history.reviewer_count} vendors`:"No approved reviews yet"}</p>
         </div>
         <div><h3 className="font-semibold text-[#252521]">Vendor requirements</h3>{detail.requirements.length>0?<ul className="mt-2 list-disc space-y-2 pl-5">{detail.requirements.map(note=><li key={note}>{note}</li>)}</ul>:<p className="mt-1 text-xs">Specific requirements are unconfirmed. Check with the organizer.</p>}</div>
         {(listed.length>0||Object.keys(evidence).length>0||coverage.length>0)&&<details className="border-t border-[#252521]/15 pt-1">
           <summary className="min-h-11 cursor-pointer py-3 font-semibold text-[#07472B]">Category evidence & source checks<span className="sr-only"> for {item.title}, {formatAttendanceDate(item.starts_on)}</span></summary>
           <div className="space-y-4 pb-2">
         <div><h3 className="font-semibold text-[#252521]">Category eligibility</h3>
           {listed.length>0&&<p className="mt-1">Listed categories: {listed.join(", ")}.</p>}

           {Object.entries(evidence).length>0&&<ul className="mt-3 space-y-3">{Object.entries(evidence).map(([category,entry])=><li key={category}>
             <p className="font-semibold">{category}: {categoryEvidenceLabel(entry)}</p><p className="mt-1">{entry.note}</p>
             <p className="mt-1 text-xs text-[#626C57]">Category checked {new Date(entry.checked_at).toLocaleDateString("en-US",{timeZone:"America/New_York"})}{safeExternalUrl(entry.source_url)&&<> · <a href={safeExternalUrl(entry.source_url)!} target="_blank" rel="noopener noreferrer" className="underline">Category source <ExternalLinkIcon /></a></>}</p>
           </li>)}</ul>}
         </div>
         {coverage.length>0&&<div><h3 className="font-semibold text-[#252521]">What the sources confirm</h3>
           <p className="mt-1 text-xs">Partial checks may not cover every price, requirement, or category.</p>
           <ul className="mt-3 grid gap-3 sm:grid-cols-2">{coverage.map(([key,fact])=><li key={key} className="border border-[#252521]/15 p-3">
             <p className="font-semibold">{coverageLabels[key]}: {coverageStatus[fact.status]}</p>
             <p className="mt-1 text-xs leading-relaxed">{fact.summary}</p>
             <p className="mt-2 text-xs">Checked {new Date(fact.checked_at).toLocaleDateString("en-US",{timeZone:"America/New_York"})}{safeExternalUrl(fact.source_url)&&<> · <a href={safeExternalUrl(fact.source_url)!} target="_blank" rel="noopener noreferrer" className="text-[#07472B] underline">Official source <ExternalLinkIcon /></a></>}</p>
           </li>)}</ul>
         </div>}
           </div>
         </details>}
         <p className="text-xs">Organizer approval is required. Confirm current terms and availability before applying; reviews describe past experiences.</p>
         {safeExternalUrl(item.source_url)&&<a href={safeExternalUrl(item.source_url)!} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center font-semibold text-[#07472B] underline">Official source <ExternalLinkIcon /></a>}
       </div>
  </div>
  <div className="sticky bottom-0 z-10 flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-[#252521]/20 bg-[#FFFCF6] px-5 py-4 sm:px-7">
   {available&&actionUrl?<a href={actionUrl} target="_blank" rel="noopener noreferrer" className="heritage-button min-h-11">{item.effective_status==="waitlist"?"Official waitlist":"Official application"} <ExternalLinkIcon /></a>:<p className="text-sm font-semibold text-[#626C57]">{item.effective_status==="closed"?"Application closed":"Application availability not verified"}</p>}
   <Link href={`/markets/${item.market_slug}`} className="inline-flex min-h-11 items-center text-sm font-semibold text-[#07472B] underline underline-offset-4">View market profile</Link>
   {sourceUrl&&<a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center text-sm font-semibold text-[#07472B] underline">Official source <ExternalLinkIcon /></a>}
  </div>
 </dialog>;
}
