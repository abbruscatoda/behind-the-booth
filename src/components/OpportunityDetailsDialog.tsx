"use client";
import ExternalLinkIcon from "./ExternalLinkIcon";
import OpportunitySourceLink from "./OpportunitySourceLink";
import Link from "next/link";
import { useEffect, useRef } from "react";
import { activeCategoryEvidence, categoryEvidenceLabel, categoryScopeNote, categorySourceTerms, categoryHighlights, listedOpportunityCategories } from "../lib/opportunityCategories";
import { currentCoverage, coverageWithFieldFacts, coverageLabels, coverageStatus } from "../lib/researchCoverage";
import { opportunityDeadline, opportunityBoothPrice, opportunityDetailSections } from "../lib/opportunityPresentation";
import { formatAttendanceDate } from "../lib/attendanceDate";
import { fee, safeExternalUrl, statusLabel, type Opportunity } from "../lib/opportunities";
import { applicationFeePresentation, moneyAmount } from "../lib/opportunityFacts";
import { opportunityApplication } from "../lib/opportunityApplication";

/** A native modal allows in-depth research without changing neighboring card heights. */
export default function OpportunityDetailsDialog({item,onClose}:{item:Opportunity;onClose:()=>void}) {
 const dialogRef=useRef<HTMLDialogElement>(null);
 useEffect(()=>{
  const dialog=dialogRef.current;
  const previousOverflow=document.body.style.overflow;
  document.body.style.overflow="hidden";
  if(dialog && !dialog.open)dialog.showModal();
  return ()=>{if(dialog?.open)dialog.close();document.body.style.overflow=previousOverflow;};
 },[]);
 const deadline=opportunityDeadline(item);
 const booth=opportunityBoothPrice(item);
 const applicationFee=applicationFeePresentation(item);
 const priceOptions=item.field_facts?.pricing_options ?? [];
 const detail=opportunityDetailSections(item);
 const deadlineNotes=[...new Set([deadline.note,...detail.notes].filter(Boolean))];
 const evidence=activeCategoryEvidence(item);
 const listed=listedOpportunityCategories(item);
 const highlights=categoryHighlights(item);
 const coverage=currentCoverage(coverageWithFieldFacts(item.research_coverage,item.field_facts));
 const application=opportunityApplication(item);
 const sourceUrl=safeExternalUrl(item.source_url);
 return <dialog ref={dialogRef}
  aria-labelledby={`opportunity-dialog-title-${item.id}`}
  onClose={onClose}
  onClick={event=>{if(event.target===event.currentTarget)dialogRef.current?.close();}}
  className="m-auto h-[90dvh] max-h-[90dvh] w-[calc(100%-2rem)] max-w-3xl overflow-hidden rounded-sm border border-[#252521]/30 bg-[#FFFCF6] p-0 text-[#252521] shadow-2xl backdrop:bg-[#252521]/60 open:flex open:flex-col"
 >
  <div className="opportunity-dialog-header grid shrink-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2 border-b border-[#252521]/20 bg-[#FFFCF6] px-4 py-3 sm:px-7 sm:py-4">
   <p className="heritage-label">Opportunity details</p>
   <button type="button" onClick={()=>dialogRef.current?.close()} className="min-h-11 rounded-sm border border-[#252521]/25 px-3 py-2 text-sm font-semibold text-[#07472B] hover:bg-[#E9E7DA] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07472B]" aria-label="Close opportunity details">Close <span aria-hidden="true">×</span></button>
   <h2 id={`opportunity-dialog-title-${item.id}`} className="opportunity-dialog-title col-span-2 min-w-0 font-serif text-xl font-bold leading-tight sm:text-3xl">{item.title}</h2>
   <p className="col-span-2 text-sm text-[#626C57]">{item.city}, {item.state} · {statusLabel(item.effective_status)}</p>
  </div>
  <div className="min-h-0 min-w-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-4 py-5 [overflow-wrap:anywhere] sm:px-7 sm:py-6">
   <div className="grid gap-4 border-b border-[#252521]/15 pb-5 text-sm sm:grid-cols-2">
    <div><p className="text-xs font-semibold uppercase tracking-wide text-[#626C57]">Organizer</p><p className="mt-1 font-semibold">{item.organizer}</p><p className="mt-1 text-[#55554E]">{item.venue} · {item.city}, {item.state}</p></div>
    <div><p className="text-xs font-semibold uppercase tracking-wide text-[#626C57]">{item.schedule_type==="rolling_market"?"Application window":item.schedule_type==="seasonal_application"||item.schedule_type==="recurring_season"?"Application / program season":"Market dates"}</p>
     <p className="mt-1 font-semibold">{item.schedule_type==="rolling_market"?"Ongoing — rolling vendor applications":formatAttendanceDate(item.starts_on)+(item.ends_on!==item.starts_on?" – "+formatAttendanceDate(item.ends_on):"")}</p>
     <p className="mt-1"><strong>{deadline.label}:</strong> {deadline.value}</p>
     {application.note&&<p className="mt-2 text-xs font-semibold text-[#07472B]">{application.note}</p>}
     {(item.schedule_type==="seasonal_application"||item.schedule_type==="recurring_season")&&<p className="mt-1 text-xs text-[#626C57]">Program coverage does not guarantee individual vending dates or booths.</p>}
    </div>
    <div><p className="text-xs font-semibold uppercase tracking-wide text-[#626C57]">{booth.label}</p><p className="mt-1 font-semibold">{booth.value}</p>{booth.note&&<p className="mt-1 text-xs">{booth.note}</p>}</div>
    <div><p className="text-xs font-semibold uppercase tracking-wide text-[#626C57]">Application fee</p><p className="mt-1 font-semibold">{applicationFee.value}</p>{applicationFee.note&&<p className="mt-1 text-xs">{applicationFee.note}</p>}{item.deposit!==null&&<p className="mt-1">Deposit: {fee(item.deposit)}</p>}</div>
   </div>
   {item.field_facts?.restrictions?.map((restriction,index)=><p key={index} className="border-l-2 border-[#AD573B] pl-3 text-sm font-semibold">{restriction}</p>)}
   {priceOptions.length>0&&<section aria-label="Published pricing options">
     <h3 className="font-semibold">Published pricing options</h3>
     <p className="mt-1 text-xs text-[#626C57]">{item.field_facts?.pricing?.summary}</p>
     <ul className="mt-3 space-y-3 text-sm">{priceOptions.map((option,index)=><li key={`${option.label}-${index}`} className="border-l-2 border-[#07472B]/30 pl-3">
       <p><strong>{option.label}: {moneyAmount(option.amount)}</strong>{option.unit==="day"?" / day":option.unit==="event"?" / event":option.unit==="season"?" / season":option.unit==="application"?" to apply":""}{!option.applicable&&<strong> · {option.unavailable ? "Unavailable at source" : "Reference only"}</strong>}</p>
       {option.conditions&&<p className="mt-1 text-xs text-[#55554E]">{option.conditions}</p>}
       <OpportunitySourceLink href={option.source_url} applicationUrl={item.application_url} className="text-xs text-[#07472B] underline" />
     </li>)}</ul>
   </section>}
   {item.field_facts?.requirements?.summary&&<section><h3 className="font-semibold">Application-specific requirements</h3><p className="mt-2 text-sm leading-relaxed">{item.field_facts.requirements.summary}</p></section>}
   {highlights.length>0&&<div className="border-l-2 border-[#AD573B] bg-[#F4F0E6] px-4 py-3">
    <h3 className="font-semibold">Product eligibility notes</h3>
    <ul className="mt-2 list-disc space-y-2 pl-4 text-sm leading-relaxed">{highlights.map(([category,entry])=><li key={category}>
      <strong>{category}: {categoryEvidenceLabel(entry)}.</strong>
      {entry.status==="eligible"&&categorySourceTerms(entry).length>0&&<p className="mt-1"><strong>Organizer’s wording:</strong> {categorySourceTerms(entry).map(term=>`“${term}”`).join("; ")}</p>}
      {entry.note&&<p className="mt-1">{entry.note}</p>}
      {entry.status==="eligible"&&<p className="mt-1 font-semibold">{categoryScopeNote(category,entry)}</p>}
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
         <div><h3 className="font-semibold text-[#252521]">Organizer wording by search group</h3>
           {listed.length>0&&<p className="mt-1">Search groups: {listed.join(", ")}.</p>}
           <p className="mt-1 text-xs">Behind the Booth groups related products for searching. These are not necessarily the organizer’s category names or approval of every product in a group.</p>

           {Object.entries(evidence).length>0&&<ul className="mt-3 space-y-3">{Object.entries(evidence).map(([category,entry])=><li key={category}>
             <p className="font-semibold">{category}: {categoryEvidenceLabel(entry)}</p><p className="mt-1">{entry.note}</p>
             {entry.status==="eligible"&&categorySourceTerms(entry).length>0&&<p className="mt-1"><strong>Organizer’s wording:</strong> {categorySourceTerms(entry).map(term=>`“${term}”`).join("; ")}</p>}
             {entry.status==="eligible"&&<p className="mt-1 text-xs">{categoryScopeNote(category,entry)}</p>}
             <p className="mt-1 text-xs text-[#626C57]">Category checked {new Date(entry.checked_at).toLocaleDateString("en-US",{timeZone:"America/New_York"})}{safeExternalUrl(entry.source_url)&&<> · <OpportunitySourceLink href={entry.source_url} applicationUrl={item.application_url} className="underline" /></>}</p>
           </li>)}</ul>}
         </div>
         {coverage.length>0&&<div><h3 className="font-semibold text-[#252521]">What the sources confirm</h3>
           <p className="mt-1 text-xs">Partial checks may not cover every price, requirement, or category.</p>
           <ul className="mt-3 grid gap-3 sm:grid-cols-2">{coverage.map(([key,fact])=><li key={key} className="border border-[#252521]/15 p-3">
             <p className="font-semibold">{coverageLabels[key]}: {coverageStatus[fact.status]}</p>
             <p className="mt-1 text-xs leading-relaxed">{fact.summary}</p>
             <p className="mt-2 text-xs">Checked {new Date(fact.checked_at).toLocaleDateString("en-US",{timeZone:"America/New_York"})}{safeExternalUrl(fact.source_url)&&<> · <OpportunitySourceLink href={fact.source_url} applicationUrl={item.application_url} className="text-[#07472B] underline" /></>}</p>
           </li>)}</ul>
         </div>}
           </div>
         </details>}
         <p className="text-xs">Organizer approval is required. Confirm current terms and availability before applying; reviews describe past experiences.</p>
         <OpportunitySourceLink href={item.source_url} applicationUrl={item.application_url} className="inline-flex min-h-11 items-center font-semibold text-[#07472B] underline" />
       </div>
  </div>
  <div className="opportunity-dialog-footer grid shrink-0 grid-cols-2 items-center gap-x-3 gap-y-2 border-t border-[#252521]/20 bg-[#FFFCF6] px-4 py-3 sm:flex sm:flex-wrap sm:gap-x-6 sm:gap-y-3 sm:px-7 sm:py-4">
   {application.href?<a href={application.href} target={application.external?"_blank":undefined} rel={application.external?"noopener noreferrer":undefined} className="heritage-button col-span-2 min-h-11 sm:w-auto">{application.label} {application.external&&<ExternalLinkIcon />}</a>:<p className="col-span-2 text-sm font-semibold text-[#626C57]">{application.label}</p>}
   <Link href={`/markets/${item.market_slug}`} className="inline-flex min-h-11 items-center text-xs font-semibold text-[#07472B] underline underline-offset-4 sm:text-sm">View market profile</Link>
   {sourceUrl&&<OpportunitySourceLink href={sourceUrl} applicationUrl={item.application_url} className="inline-flex min-h-11 items-center text-xs font-semibold text-[#07472B] underline sm:text-sm" />}
  </div>
 </dialog>;
}
