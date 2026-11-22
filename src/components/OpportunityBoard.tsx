"use client";
import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import OpportunityCard from "./OpportunityCard";
import OpportunityDetailsDialog from "./OpportunityDetailsDialog";
import { createClient } from "../lib/supabase/client";
import { isNewlyPosted, isPostedSince } from "../lib/opportunityRecency";
import { opportunityCategoryStatus } from "../lib/opportunityCategories";
import { filterOpportunities, sortOpportunities, statusLabel, VENDOR_CATEGORIES, type Opportunity, type OpportunitySort, type OpportunityFilters } from "../lib/opportunities";
import { defaultOpportunityFilters, defaultOpportunitySort, readOpportunitySearch, writeOpportunitySearch } from "../lib/opportunitySearchUrl";

/** Counts only selections tucked into the optional panel. */
function additionalFilterCount(filters: OpportunityFilters): number {
 return Number(Boolean(filters.month))
  + Number((filters.schedule??"all")!=="all")
  + Number((filters.priceAvailability??"all")!=="all")
  + Number(Boolean(filters.maxBoothFee))
  + Number(Boolean(filters.deadlineBefore));
}
export default function OpportunityBoard({ marketId, compact = false }: { marketId?: string; compact?: boolean }) {
 const [items,setItems]=useState<Opportunity[]>([]), [loading,setLoading]=useState(true), [error,setError]=useState("");
 const [filters,setFilters]=useState({...defaultOpportunityFilters});
 const [urlReady,setUrlReady]=useState(false),[shareMessage,setShareMessage]=useState("");
 const [sort,setSort]=useState<OpportunitySort>(defaultOpportunitySort),[refresh,setRefresh]=useState(0),[saved,setSaved]=useState<string[]>([]),[saving,setSaving]=useState<string|null>(null),[message,setMessage]=useState("");
 const [selectedOpportunity,setSelectedOpportunity]=useState<Opportunity|null>(null);
 const [messageOpportunityId,setMessageOpportunityId]=useState<string|null>(null);
 const [moreFiltersOpen,setMoreFiltersOpen]=useState(false);
 const [lastVisit,setLastVisit]=useState<string|null>(null);
 const [reviewedAt,setReviewedAt]=useState(0);
 const moreFiltersId=useId();
 useEffect(()=>{
  if(message&&messageOpportunityId)document.getElementById(`opportunity-save-message-${messageOpportunityId}`)?.scrollIntoView({block:"nearest"});
 },[message,messageOpportunityId]);

 // The baseline is browser-local and kept stable throughout this tab's session.
 // Do not call a list "viewed": visiting the page isn't proof of reading every card.
 useEffect(()=>{
  if(compact || marketId)return;
  const localKey="btb_opportunities_last_opened_v1";
  const sessionKey="btb_opportunities_session_baseline_v1";
  const now=Date.now();
  let previous:string|null=null;
  try{
   const sessionBaseline=window.sessionStorage.getItem(sessionKey);
   if(sessionBaseline!==null)previous=sessionBaseline||null;
   else{
    previous=window.localStorage.getItem(localKey);
    window.sessionStorage.setItem(sessionKey,previous??"");
   }
   window.localStorage.setItem(localKey,new Date(now).toISOString());
  }catch{
   // Browsing remains fully functional with storage disabled.
  }
  const timestamp=previous?Date.parse(previous):NaN;
  setLastVisit(Number.isFinite(timestamp)&&timestamp<=now?previous:null);
 },[compact,marketId]);
 useEffect(()=>{
  if(compact || marketId)return;
  const fromUrl=()=>{const state=readOpportunitySearch(new URLSearchParams(window.location.search));setFilters(state.filters);setSort(state.sort);setMoreFiltersOpen(additionalFilterCount(state.filters)>0);};
  fromUrl();
  setUrlReady(true);
  window.addEventListener("popstate",fromUrl);
  return()=>window.removeEventListener("popstate",fromUrl);
 },[compact,marketId]);
 useEffect(()=>{
  if(!urlReady || compact || marketId)return;
  const next=writeOpportunitySearch(new URL(window.location.href),filters,sort);
  if(next.href!==window.location.href)window.history.replaceState(window.history.state,"",next.href);
 },[filters,sort,urlReady,compact,marketId]);
 async function copySearchLink(){
  const url=writeOpportunitySearch(new URL(window.location.href),filters,sort);
  try{await navigator.clipboard.writeText(url.href);setShareMessage(filters.posted==="since"?"Search link copied. The since-last-visit view is specific to this browser, so it is not included in the link.":"Search link copied.");}
  catch{setShareMessage("Unable to copy automatically. Copy the address from your browser.");}
 }
 useEffect(()=>{let active=true;const client=createClient();const subscription=client.auth.onAuthStateChange(()=>{if(active)setSaved([]);});
 async function load(){setLoading(true);setError("");try{let all:Opportunity[]=[];let offset=0;while(true){const {data,error}=await client.rpc("btb_public_opportunities",{p_market_id:marketId??null,p_offset:offset});if(error)throw error;all=all.concat(data.items);offset+=100;if(offset>=data.total||data.items.length===0)break;}if(active){setReviewedAt(Date.now());setItems(all);}
 const {data:auth}=await client.auth.getUser();if(auth.user){const {data,error}=await client.rpc("btb_my_saved_opportunities");if(!error&&active)setSaved((data as {id:string}[]).map(row=>row.id));}
 }catch{if(active)setError("We couldn't load application opportunities. Please refresh to try again.");}finally{if(active)setLoading(false);}}
 void load();const timer=setInterval(()=>{if(document.visibilityState==="visible")setRefresh(value=>value+1);},300000);
 return()=>{active=false;clearInterval(timer);subscription.data.subscription.unsubscribe();};},[marketId,refresh]);
 async function toggle(id:string){if(saving)return;setSaving(id);setMessage("");setMessageOpportunityId(id);try{const client=createClient();const {data}=await client.auth.getUser();if(!data.user){setMessage("Sign in to save opportunities, then return here. Browsing and application links are free to use.");return;}const add=!saved.includes(id);const {error}=await client.rpc("btb_save_opportunity",{p_id:id,p_saved:add});if(error)throw error;setSaved(previous=>add?[...previous,id]:previous.filter(value=>value!==id));setMessage(add?"Saved to My Account.":"Removed from saved opportunities.");}catch{setMessage("Unable to update your saved opportunities. Please try again.");}finally{setSaving(null);}}
 const followedHash=useRef<string|null>(null);
 useEffect(()=>{
  if(loading||error)return;
  let id:string;
  try{id=decodeURIComponent(window.location.hash.slice(1));}catch{return;}
  if(!id||followedHash.current===id)return;
  const target=document.getElementById(id);
  if(target){target.scrollIntoView({block:"start"});followedHash.current=id;}
 },[loading,error,items]);
 const visible=sortOpportunities(filterOpportunities(items,filters,lastVisit,reviewedAt),sort);
 const cards=compact?visible.slice(0,3):visible;
 const activeItems=items.filter(item=>["open","limited","waitlist"].includes(item.effective_status));
 const recentCount=activeItems.filter(item=>isNewlyPosted(item,reviewedAt)).length;
 const sinceCount=lastVisit?activeItems.filter(item=>isPostedSince(item,lastVisit,reviewedAt)).length:0;
 const selectPosted=(mode:"week"|"since")=>{
  setFilters(previous=>({...previous,posted:previous.posted===mode?"all":mode}));
  setSort("posted_desc");
 };
 const unconfirmedCount=filters.category ? visible.filter(item=>opportunityCategoryStatus(item,filters.category)==="unknown").length : 0;
 const additionalCount=additionalFilterCount(filters);
 const input="mt-1.5 h-11 w-full min-w-0 rounded-none border border-[#252521]/25 bg-[#FFFCF6] px-3 text-sm font-medium text-[#252521] outline-none transition-colors focus:border-[#07472B] focus-visible:ring-1 focus-visible:ring-[#07472B]";
 const controlLabel="block min-w-0 text-[11px] font-bold uppercase tracking-[0.055em] text-[#626C57]";
 const action="inline-flex min-h-10 items-center text-sm font-semibold text-[#07472B] underline underline-offset-4 hover:decoration-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07472B]";
 const resetAll=()=>{setFilters({...defaultOpportunityFilters});setSort(defaultOpportunitySort);setMoreFiltersOpen(false);setShareMessage("");};
 const additionalChips:{label:string;clear:()=>void}[]=[];
 if(filters.month)additionalChips.push({label:"Month: "+filters.month,clear:()=>setFilters(previous=>({...previous,month:""}))});
 if((filters.schedule??"all")!=="all")additionalChips.push({
  label:"Type: "+(filters.schedule==="dated"?"Dated events":filters.schedule==="seasonal"?"Seasonal":"Ongoing"),
  clear:()=>setFilters(previous=>({...previous,schedule:"all"}))
 });
 if((filters.priceAvailability??"all")!=="all")additionalChips.push({
  label:filters.priceAvailability==="published"?"With booth prices":"Unverified booth prices",
  clear:()=>setFilters(previous=>({...previous,priceAvailability:"all"}))
 });
 if(filters.maxBoothFee)additionalChips.push({label:"Max booth: $"+filters.maxBoothFee,clear:()=>setFilters(previous=>({...previous,maxBoothFee:""}))});
 if(filters.deadlineBefore)additionalChips.push({label:"Deadline by: "+filters.deadlineBefore,clear:()=>setFilters(previous=>({...previous,deadlineBefore:""}))});
 return <div>
 {!compact&&<section aria-label="Newly posted vendor opportunities"
  className="mt-5 border-y border-[#252521]/20 bg-[#E9E7DA]/55 px-4 py-3 sm:px-5">
  <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
   <div>
    <p className="text-[11px] font-bold uppercase tracking-[0.09em] text-[#626C57]">Newly posted opportunities</p>
    <p className="mt-1 text-sm text-[#55554E]">{loading?"Checking recent postings…":recentCount===0?"No new open opportunities posted in the last 7 days.":`${recentCount} new ${recentCount===1?"opportunity":"opportunities"} posted in the last 7 days.`}</p>
    {!lastVisit&&<p className="mt-1 text-xs text-[#626C57]">On a future visit in this browser, you can also see what appeared since today.</p>}
   </div>
   <div className="flex flex-wrap gap-2">
    <button type="button" disabled={loading||recentCount===0} aria-pressed={filters.posted==="week"}
     onClick={()=>selectPosted("week")}
     className={`min-h-10 border px-3 py-2 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07472B] disabled:cursor-not-allowed disabled:opacity-50 ${filters.posted==="week"?"border-[#07472B] bg-[#07472B] text-white":"border-[#07472B]/40 text-[#07472B] hover:bg-[#DFE2D5]"}`}>
     New this week ({recentCount})
    </button>
    {lastVisit&&<button type="button" disabled={loading||sinceCount===0} aria-pressed={filters.posted==="since"}
     onClick={()=>selectPosted("since")}
     className={`min-h-10 border px-3 py-2 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07472B] disabled:cursor-not-allowed disabled:opacity-50 ${filters.posted==="since"?"border-[#07472B] bg-[#07472B] text-white":"border-[#07472B]/40 text-[#07472B] hover:bg-[#DFE2D5]"}`}>
     Since last visit ({sinceCount})
    </button>}
    {filters.posted&&filters.posted!=="all"&&<button type="button"
     onClick={()=>setFilters(previous=>({...previous,posted:"all"}))}
     className="min-h-10 px-2 text-xs font-semibold text-[#07472B] underline underline-offset-4">Show all</button>}
   </div>
  </div>
 </section>}
 {!compact&&<section aria-label="Search and filter vendor opportunities" className="mt-6 border-y border-[#252521]/20 py-4">
  <div className="grid gap-x-4 gap-y-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)_minmax(0,1fr)]">
   <label className={controlLabel+" sm:col-span-2 lg:col-span-1"}>Search opportunities
    <input className={input} type="search" value={filters.search} onChange={event=>setFilters({...filters,search:event.target.value})} placeholder="Market, organizer, city, or venue…" />
   </label>
   <label className={controlLabel}>Vendor category
    <select className={input} value={filters.category} onChange={event=>setFilters({...filters,category:event.target.value})}>
     <option value="">All categories</option>
     {VENDOR_CATEGORIES.map(category=><option key={category}>{category}</option>)}
    </select>
   </label>
   <label className={controlLabel}>Location
    <select className={input} value={filters.city} onChange={event=>setFilters({...filters,city:event.target.value})}>
     <option value="">All locations</option>
     {[...new Set(items.map(item=>item.city))].sort().map(city=><option key={city}>{city}</option>)}
    </select>
   </label>
  </div>
  <div className="mt-3 flex flex-wrap items-end gap-x-4 gap-y-3">
   <label className={controlLabel+" min-w-[175px] flex-[1_1_190px] sm:max-w-[290px]"}>Application status
    <select className={input} value={filters.status} onChange={event=>setFilters({...filters,status:event.target.value})}>
     <option value="active">Open, limited or waitlisted</option>
     {["all","open","limited","waitlist","needs_recheck","closed"].map(status=><option key={status} value={status}>{status==="all"?"All statuses":statusLabel(status)}</option>)}
    </select>
   </label>
   <label className={controlLabel+" min-w-[175px] flex-[1_1_190px] sm:max-w-[290px]"}>Sort by
    <select className={input} value={sort} onChange={event=>setSort(event.target.value as OpportunitySort)}>
     <option value="date">Upcoming event date</option>
     <option value="posted_desc">Newest posted first</option>
     <option value="deadline">Application deadline (confirmed first)</option>
     <option value="fee_asc">Booth fee (lowest verified first)</option>
     <option value="rating_desc">Vendor rating (reviewed first)</option>
    </select>
   </label>
   <button type="button" aria-expanded={moreFiltersOpen} aria-controls={moreFiltersId}
    onClick={()=>setMoreFiltersOpen(open=>!open)}
    className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 border border-[#07472B]/45 bg-[#E9E7DA] px-4 text-sm font-bold text-[#07472B] hover:border-[#07472B] hover:bg-[#DFE2D5] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07472B]">
    <span aria-hidden="true" className="text-lg leading-none">{moreFiltersOpen?"−":"+"}</span>
    {moreFiltersOpen?"Fewer filters":"More filters"}
    {additionalCount>0&&<span className="flex min-h-5 min-w-5 items-center justify-center rounded-full bg-[#07472B] px-1 text-[11px] font-bold text-white" aria-label={additionalCount+" additional filters selected"}>{additionalCount}</span>}
   </button>
  </div>
  {filters.category&&<div className="mt-3">
   <label className="flex min-h-8 cursor-pointer items-center gap-2 text-xs font-medium text-[#55554E]">
    <input type="checkbox" checked={filters.includeUnconfirmed} onChange={event=>setFilters({...filters,includeUnconfirmed:event.target.checked})} aria-describedby="opportunity-unconfirmed-category-help" className="accent-[#07472B]" />
    Include opportunities where this category is unconfirmed
   </label>
   <p id="opportunity-unconfirmed-category-help" className="text-xs leading-relaxed text-[#626C57]">Unconfirmed categories are possible matches, not organizer-approved categories.</p>
  </div>}
  <div id={moreFiltersId} role="region" aria-label="Additional opportunity filters"
   className={(moreFiltersOpen?"grid":"hidden")+" mt-4 gap-x-4 gap-y-4 border-t border-[#252521]/15 bg-[#E9E7DA]/45 px-3 py-4 sm:grid-cols-2 lg:grid-cols-3 sm:px-4"}>
   <label className={controlLabel}>Opportunity type
    <select className={input} value={filters.schedule??"all"} onChange={event=>setFilters({...filters,schedule:event.target.value as "all"|"dated"|"seasonal"|"ongoing"})}>
     <option value="all">All opportunities</option><option value="dated">Dated events</option>
     <option value="seasonal">Seasonal applications / waitlists</option>
     <option value="ongoing">Ongoing / rolling applications</option>
    </select>
   </label>
   <label className={controlLabel}>Event month
    <input className={input} type="month" value={filters.month} onChange={event=>setFilters({...filters,month:event.target.value})} />
   </label>
   <label className={controlLabel}>Booth price information
    <select className={input} value={filters.priceAvailability} onChange={event=>setFilters({...filters,priceAvailability:event.target.value as "all"|"published"|"unpublished"})}>
     <option value="all">Any price information</option>
     <option value="published">Verified price only</option>
     <option value="unpublished">Price not verified</option>
    </select>
   </label>
   <label className={controlLabel}>Maximum verified booth fee ($)
    <input className={input} type="number" min="0" step="1" inputMode="numeric" value={filters.maxBoothFee} onChange={event=>setFilters({...filters,maxBoothFee:event.target.value,priceAvailability:event.target.value?"all":filters.priceAvailability})} placeholder="No maximum" />
   </label>
   <label className={controlLabel}>Application deadline on or before
    <input className={input} type="date" value={filters.deadlineBefore} onChange={event=>setFilters({...filters,deadlineBefore:event.target.value})} />
   </label>
   <p className="self-end pb-1 text-xs leading-relaxed text-[#626C57]">
    Booth prices must be independently verified; missing prices are never treated as free. Deadline filters use confirmed cutoffs, not estimated dates.
   </p>
  </div>
  {!moreFiltersOpen&&additionalChips.length>0&&<div className="mt-3 flex flex-wrap items-center gap-2" aria-label="Selected additional filters">
   <span className="mr-1 text-xs font-semibold text-[#626C57]">Also filtering by:</span>
   {additionalChips.map(chip=><button type="button" key={chip.label} onClick={chip.clear}
    aria-label={"Remove "+chip.label+" filter"}
    className="inline-flex min-h-8 items-center gap-2 border border-[#07472B]/25 bg-[#E9E7DA] px-2.5 py-1 text-xs font-semibold text-[#07472B] hover:border-[#07472B] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#07472B]">
     {chip.label}<span aria-hidden="true">×</span>
    </button>)}
  </div>}
  <div className="mt-4 flex flex-wrap items-center justify-between gap-x-5 gap-y-2 border-t border-[#252521]/15 pt-3">
   <p role="status" className="text-sm text-[#55554E]">
    {loading?"Checking opportunities…":<><strong className="text-[#252521]">{visible.length}</strong> {visible.length===1?"opportunity":"opportunities"}{unconfirmedCount?" · "+unconfirmedCount+" categories unconfirmed":""}</>}
   </p>
   <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
    <button type="button" onClick={()=>void copySearchLink()} className={action}>Copy search link</button>
    <button type="button" onClick={resetAll} className={action}>Clear filters</button>
    {filters.status!=="all"&&<button type="button" onClick={()=>setFilters(previous=>({...previous,status:"all"}))} className={action}>Show all statuses</button>}
   </div>
  </div>
  {shareMessage&&<p role="status" className="mt-2 text-xs text-[#07472B]">{shareMessage}</p>}
 </section>}
 {!compact&&sort==="deadline"&&<p className="mt-3 text-xs leading-relaxed text-[#626C57]">Event-specific deadlines appear first. Series deadlines and unconfirmed cutoffs appear afterward, ordered by event date.</p>}
 {!compact&&filters.posted==="since"&&lastVisit&&<p className="mt-3 text-xs text-[#626C57]">Showing opportunities first published since your previous visit to this page on this browser.</p>}
 {message&&!cards.some(item=>item.id===messageOpportunityId)&&<p role="status" className="my-5 border-l-2 border-[#07472B] bg-[#E9E7DA] p-4 text-sm">{message} <Link href="/login" className="font-semibold underline">My Account →</Link></p>}
 {error?<div role="alert" className="mt-6"><p>{error}</p><button onClick={()=>setRefresh(value=>value+1)} className="mt-3 font-semibold underline">Refresh opportunities</button></div>:loading?<p role="status" className="mt-6">Loading opportunities…</p>:visible.length===0?<p className="mt-6 text-[#55554E]">{compact?"No recently verified vendor applications or waitlists are listed for this market right now.":"No opportunities match these filters. Try another location or month, include unconfirmed categories, or show all statuses."}</p>:<div className={`mt-5 grid items-stretch gap-5 ${compact?"":"md:grid-cols-2 lg:grid-cols-3"}`}>
 {cards.map(item=><OpportunityCard
   key={item.id}
   item={item}
   categoryFilter={filters.category}
   saved={saved.includes(item.id)}
   saving={saving!==null}
   saveMessage={messageOpportunityId===item.id?message:""}
   onSave={()=>void toggle(item.id)}
   onViewDetails={()=>setSelectedOpportunity(item)}
 />)}
 </div>}
 {selectedOpportunity&&<OpportunityDetailsDialog item={selectedOpportunity} onClose={()=>setSelectedOpportunity(null)} />}
 </div>;
}
