"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { createClient } from "../lib/supabase/client";
import { activeCategoryEvidence, categoryEvidenceLabel, categoryHighlights, listedOpportunityCategories, opportunityCategoryStatus } from "../lib/opportunityCategories";
import { currentCoverage, coverageLabels, coverageStatus } from "../lib/researchCoverage";
import { opportunityDeadline, opportunityBoothPrice, publicOpportunityCopy } from "../lib/opportunityPresentation";
import { formatAttendanceDate } from "../lib/attendanceDate";
import { filterOpportunities, fee, safeExternalUrl, statusLabel, VENDOR_CATEGORIES, type Opportunity } from "../lib/opportunities";

const defaultFilters = {search:"",city:"",month:"",category:"",status:"active",includeUnconfirmed:true};

export default function OpportunityBoard({ marketId, compact = false }: { marketId?: string; compact?: boolean }) {
 const [items,setItems]=useState<Opportunity[]>([]), [loading,setLoading]=useState(true), [error,setError]=useState("");
 const [filters,setFilters]=useState({...defaultFilters});
 const [sort,setSort]=useState("date"),[refresh,setRefresh]=useState(0),[saved,setSaved]=useState<string[]>([]),[saving,setSaving]=useState<string|null>(null),[message,setMessage]=useState("");
 useEffect(()=>{let active=true;const client=createClient();const subscription=client.auth.onAuthStateChange(()=>{if(active)setSaved([]);});
 async function load(){setLoading(true);setError("");try{let all:Opportunity[]=[];let offset=0;while(true){const {data,error}=await client.rpc("btb_public_opportunities",{p_market_id:marketId??null,p_offset:offset});if(error)throw error;all=all.concat(data.items);offset+=100;if(offset>=data.total||data.items.length===0)break;}if(active)setItems(all);
 const {data:auth}=await client.auth.getUser();if(auth.user){const {data,error}=await client.rpc("btb_my_saved_opportunities");if(!error&&active)setSaved((data as {id:string}[]).map(row=>row.id));}
 }catch{if(active)setError("We couldn't load application opportunities. Please refresh to try again.");}finally{if(active)setLoading(false);}}
 void load();const timer=setInterval(()=>{if(document.visibilityState==="visible")setRefresh(value=>value+1);},300000);
 return()=>{active=false;clearInterval(timer);subscription.data.subscription.unsubscribe();};},[marketId,refresh]);
 async function toggle(id:string){if(saving)return;setSaving(id);setMessage("");try{const client=createClient();const {data}=await client.auth.getUser();if(!data.user){setMessage("Sign in to save opportunities, then return here. Browsing and application links are free to use.");return;}const add=!saved.includes(id);const {error}=await client.rpc("btb_save_opportunity",{p_id:id,p_saved:add});if(error)throw error;setSaved(previous=>add?[...previous,id]:previous.filter(value=>value!==id));setMessage(add?"Saved to My Account.":"Removed from saved opportunities.");}catch{setMessage("Unable to update your saved opportunities. Please try again.");}finally{setSaving(null);}}
 const followedHash=useRef<string|null>(null);
 useEffect(()=>{
  if(loading||error)return;
  let id:string;
  try{id=decodeURIComponent(window.location.hash.slice(1));}catch{return;}
  if(!id||followedHash.current===id)return;
  const target=document.getElementById(id);
  if(target){target.scrollIntoView({block:"start"});followedHash.current=id;}
 },[loading,error,items]);
 const visible=filterOpportunities(items,filters).sort((a,b)=>sort==="deadline"?(opportunityDeadline(a).sortAt-opportunityDeadline(b).sortAt || a.starts_on.localeCompare(b.starts_on)):a.starts_on.localeCompare(b.starts_on));
 const unconfirmedCount=filters.category ? visible.filter(item=>opportunityCategoryStatus(item,filters.category)==="unknown").length : 0;
 const input="mt-2 w-full min-w-0 border border-[#252521]/25 bg-[#FFFCF6] px-3 py-3 text-sm outline-none focus:border-[#07472B]";
 return <div>
 {!compact&&<div className="mt-6 border-y border-[#252521]/20 py-4"><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
 <label className="text-xs font-bold text-[#626C57]">SEARCH MARKETS OR ORGANIZERS<input className={input} value={filters.search} onChange={event=>setFilters({...filters,search:event.target.value})} placeholder="Search opportunities…"/></label>
 <label className="text-xs font-bold text-[#626C57]">LOCATION<select className={input} value={filters.city} onChange={event=>setFilters({...filters,city:event.target.value})}><option value="">All locations</option>{[...new Set(items.map(item=>item.city))].sort().map(city=><option key={city}>{city}</option>)}</select></label>
 <label className="text-xs font-bold text-[#626C57]">EVENT MONTH<input type="month" className={input} value={filters.month} onChange={event=>setFilters({...filters,month:event.target.value})}/></label>
 <label className="text-xs font-bold text-[#626C57]">VENDOR CATEGORY<select className={input} value={filters.category} onChange={event=>setFilters({...filters,category:event.target.value})}><option value="">All categories</option>{VENDOR_CATEGORIES.map(category=><option key={category}>{category}</option>)}</select></label>
 <label className="text-xs font-bold text-[#626C57]">APPLICATION STATUS<select className={input} value={filters.status} onChange={event=>setFilters({...filters,status:event.target.value})}><option value="active">Open or limited</option>{["all","open","limited","waitlist","needs_recheck","closed"].map(status=><option key={status} value={status}>{status==="all"?"All statuses":statusLabel(status)}</option>)}</select></label>
 <label className="text-xs font-bold text-[#626C57]">SORT<select className={input} value={sort} onChange={event=>setSort(event.target.value)}><option value="date">Upcoming event date</option><option value="deadline">Application deadline</option></select></label>
 </div>
 {filters.category&&<div className="mt-4"><label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" checked={filters.includeUnconfirmed} onChange={event=>setFilters({...filters,includeUnconfirmed:event.target.checked})} aria-describedby="unconfirmed-category-help"/>Include opportunities with unconfirmed categories</label><p id="unconfirmed-category-help" className="text-xs leading-relaxed text-[#626C57]">Unconfirmed listings may accept your category; check with the organizer. They are not confirmed matches.</p></div>}
 <div className="mt-3 flex flex-wrap items-center justify-between gap-3"><p role="status" className="text-sm text-[#55554E]">{loading?"Checking opportunities…":`${visible.length} ${visible.length===1?"opportunity":"opportunities"}${unconfirmedCount?` · ${unconfirmedCount} with unconfirmed categories`:""}`}</p><div className="flex flex-wrap gap-x-5"><button type="button" onClick={()=>{setFilters({...defaultFilters});setSort("date");}} className="min-h-11 text-sm font-semibold text-[#07472B] underline">Clear filters</button>{filters.status!=="all"&&<button type="button" onClick={()=>setFilters({...filters,status:"all"})} className="min-h-11 text-sm font-semibold text-[#07472B] underline">Show all statuses</button>}</div></div></div>}
 {!compact&&sort==="deadline"&&<p className="mt-3 text-xs leading-relaxed text-[#626C57]">Event-specific deadlines appear first. Series deadlines and unconfirmed cutoffs appear afterward, ordered by event date.</p>}
 {message&&<p role="status" className="my-5 border-l-2 border-[#07472B] bg-[#E9E7DA] p-4 text-sm">{message} <Link href="/login" className="font-semibold underline">My Account →</Link></p>}
 {error?<div role="alert" className="mt-6"><p>{error}</p><button onClick={()=>setRefresh(value=>value+1)} className="mt-3 font-semibold underline">Refresh opportunities</button></div>:loading?<p role="status" className="mt-6">Loading opportunities…</p>:visible.length===0?<p className="mt-6 text-[#55554E]">{compact?"No recently verified open applications are listed for this market right now.":"No opportunities match these filters. Try another location or month, include unconfirmed categories, or show all statuses."}</p>:<div className={`mt-5 grid gap-5 ${compact?"":"lg:grid-cols-2"}`}>
 {(compact?visible.slice(0,3):visible).map(item=>{
   const deadline=opportunityDeadline(item);
   const booth=opportunityBoothPrice(item);
   const evidence=activeCategoryEvidence(item);
   const listed=listedOpportunityCategories(item);
   const highlights=categoryHighlights(item);
   const coverage=currentCoverage(item.research_coverage);
   const selected=filters.category ? evidence[filters.category] : undefined;
   const categoryText=filters.category
     ? opportunityCategoryStatus(item,filters.category)==="eligible" ? `${filters.category} — listed by organizer` : `${filters.category} — unconfirmed`
     : listed.length ? `${listed.slice(0,3).join(", ")}${listed.length>3?` +${listed.length-3} more`:""}` : "Unconfirmed — check with organizer";
   return <article key={item.id} id={item.id} className="heritage-card scroll-mt-8 flex flex-col">
     <div className="flex flex-wrap items-center justify-between gap-3">
       <p className="heritage-label">{statusLabel(item.effective_status)}</p>
       <p className="text-xs text-[#626C57]">{item.verified_at?`Checked ${new Date(item.verified_at).toLocaleDateString("en-US",{timeZone:"America/New_York"})}`:"Not verified"}</p>
     </div>
     <h2 className="mt-4 font-serif text-2xl font-bold sm:text-3xl"><Link href={`/markets/${item.market_slug}`} className="text-inherit hover:text-[#07472B] hover:underline underline-offset-4">{item.title}</Link></h2>
     <p className="mt-2 text-sm font-semibold text-[#07472B]">{item.organizer}</p>
     <p className="mt-3 text-base font-semibold">{formatAttendanceDate(item.starts_on)}{item.ends_on!==item.starts_on?` – ${formatAttendanceDate(item.ends_on)}`:""}</p>
     <p className="mt-1 text-sm text-[#55554E]">{item.venue} · {item.city}, {item.state}</p>
     <p className="mt-3 text-sm"><strong>{deadline.label}:</strong> {deadline.value}</p>
     <p className="mt-2 text-sm"><strong>Listed categories:</strong> {categoryText}</p>
     <p className="mt-1 text-xs text-[#626C57]">This list may be incomplete; other categories may be considered.</p>
     {highlights.length>0&&<ul className="mt-3 space-y-2 border-l-2 border-[#AD573B] pl-3 text-xs leading-relaxed">{highlights.map(([category,entry])=><li key={category}>
       <span className="font-semibold">{category}: {categoryEvidenceLabel(entry)}.</span> {entry.note}
       {entry.application_deadline&&Number.isFinite(Date.parse(entry.application_deadline))&&<span> Separate deadline: {new Date(entry.application_deadline).toLocaleString("en-US",{timeZone:"America/New_York",month:"short",day:"numeric",year:"numeric",hour:"numeric",minute:"2-digit"})} Eastern.</span>}
       {entry.application_state&&safeExternalUrl(entry.source_url)&&<> <a href={safeExternalUrl(entry.source_url)!} target="_blank" rel="noopener noreferrer" className="font-semibold text-[#07472B] underline">View separate application ↗</a></>}
     </li>)}</ul>}
     {selected?.note&&!highlights.some(([category])=>category===filters.category)&&<p className="mt-2 text-xs leading-relaxed text-[#626C57]">{selected.note}</p>}
     <dl className="mt-3 grid grid-cols-3 gap-3 border-y border-[#252521]/15 py-3 text-sm">
       <div><dt className="text-xs text-[#626C57]">{booth.label}</dt><dd>{booth.value}</dd></div>
       <div><dt className="text-xs text-[#626C57]">Application fee</dt><dd>{fee(item.application_fee)}</dd></div>
       <div><dt className="text-xs text-[#626C57]">Deposit</dt><dd>{fee(item.deposit)}</dd></div>
     </dl>
     {booth.note&&<p className="mt-1 text-xs font-semibold text-[#07472B]">{booth.note}</p>}
     <p className="mt-1 text-xs text-[#626C57]">Other booth options, add-ons, and processing fees may differ. See fee details below.</p>
     <div className="mt-3 text-sm"><Link href={`/markets/${item.market_slug}#vendor-reviews`} className="font-semibold text-[#07472B] underline">{item.history.review_count?"Read vendor reviews →":"View market & add a review →"}</Link>
       <p className="mt-1 text-xs text-[#626C57]">{item.history.review_count?`${item.history.overall}/5 · ${item.history.review_count} reviews from ${item.history.reviewer_count} vendors`:"No approved reviews yet"}</p>
     </div>
     <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2">
       {["open","limited","waitlist"].includes(item.effective_status)&&safeExternalUrl(item.application_url)
         ? <a href={safeExternalUrl(item.application_url)!} target="_blank" rel="noopener noreferrer" className="heritage-button">{item.effective_status==="waitlist"?"Official waitlist":"Official application"} ↗</a>
         : <span className="text-sm text-[#626C57]">{item.effective_status==="closed"?"Application closed":"Recheck with organizer before applying"}</span>}
       <button disabled={saving!==null} onClick={()=>void toggle(item.id)} className="min-h-11 text-sm font-semibold text-[#07472B] underline disabled:opacity-50">{saved.includes(item.id)?"Saved — remove":"Save opportunity"}</button>
     </div>
     <details className="mt-4 border-t border-[#252521]/15 pt-1 text-sm">
       <summary className="min-h-11 cursor-pointer py-3 font-semibold text-[#07472B]">More details<span className="sr-only"> for {item.title}, {formatAttendanceDate(item.starts_on)}</span></summary>
       <div className="space-y-4 pb-2 leading-relaxed text-[#55554E]">
         {deadline.note&&<p>{deadline.note}</p>}
         {item.fee_notes&&<div><h3 className="font-semibold text-[#252521]">Fee details</h3><p className="mt-1 whitespace-pre-wrap">{publicOpportunityCopy(item.fee_notes)}</p></div>}
         {item.eligibility&&<div><h3 className="font-semibold text-[#252521]">Vendor requirements</h3><p className="mt-1 whitespace-pre-wrap">{publicOpportunityCopy(item.eligibility)}</p></div>}
         <div><h3 className="font-semibold text-[#252521]">Category eligibility</h3>
           {listed.length>0&&<p className="mt-1">Listed categories: {listed.join(", ")}.</p>}
           <p className="mt-1 text-xs">Other categories may be unconfirmed. A listed category is not a guarantee of space or acceptance; the organizer must approve your products.</p>
           {Object.entries(evidence).length>0&&<ul className="mt-3 space-y-3">{Object.entries(evidence).map(([category,entry])=><li key={category}>
             <p className="font-semibold">{category}: {categoryEvidenceLabel(entry)}</p><p className="mt-1">{entry.note}</p>
             <p className="mt-1 text-xs text-[#626C57]">Category checked {new Date(entry.checked_at).toLocaleDateString("en-US",{timeZone:"America/New_York"})}{safeExternalUrl(entry.source_url)&&<> · <a href={safeExternalUrl(entry.source_url)!} target="_blank" rel="noopener noreferrer" className="underline">Category source ↗</a></>}</p>
           </li>)}</ul>}
         </div>
         {coverage.length>0&&<div><h3 className="font-semibold text-[#252521]">What the sources confirm</h3>
           <p className="mt-1 text-xs">These checks describe what the official pages support. They do not guarantee acceptance, space, or that all requirements have been captured.</p>
           <ul className="mt-3 grid gap-3 sm:grid-cols-2">{coverage.map(([key,fact])=><li key={key} className="border border-[#252521]/15 p-3">
             <p className="font-semibold">{coverageLabels[key]}: {coverageStatus[fact.status]}</p>
             <p className="mt-1 text-xs leading-relaxed">{fact.summary}</p>
             <p className="mt-2 text-xs">Checked {new Date(fact.checked_at).toLocaleDateString("en-US",{timeZone:"America/New_York"})}{safeExternalUrl(fact.source_url)&&<> · <a href={safeExternalUrl(fact.source_url)!} target="_blank" rel="noopener noreferrer" className="text-[#07472B] underline">Official source ↗</a></>}</p>
           </li>)}</ul>
         </div>}
         <p className="text-xs">Review scores reflect past market experiences, not this upcoming date. Confirm current fees, requirements, and availability before applying.</p>
         {safeExternalUrl(item.source_url)&&<a href={safeExternalUrl(item.source_url)!} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-11 items-center font-semibold text-[#07472B] underline">Official source ↗</a>}
       </div>
     </details>
   </article>;
 })}
 </div>}
 </div>;
}
