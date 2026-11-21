"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import OpportunityCard from "./OpportunityCard";
import OpportunityDetailsDialog from "./OpportunityDetailsDialog";
import { createClient } from "../lib/supabase/client";
import { opportunityCategoryStatus } from "../lib/opportunityCategories";
import { filterOpportunities, sortOpportunities, VENDOR_CATEGORIES, type Opportunity, type OpportunitySort } from "../lib/opportunities";
import { defaultOpportunityFilters, defaultOpportunitySort, readOpportunitySearch, writeOpportunitySearch } from "../lib/opportunitySearchUrl";

export default function OpportunityBoard({ marketId, compact = false }: { marketId?: string; compact?: boolean }) {
 const [items,setItems]=useState<Opportunity[]>([]), [loading,setLoading]=useState(true), [error,setError]=useState("");
 const [filters,setFilters]=useState({...defaultOpportunityFilters});
 const [urlReady,setUrlReady]=useState(false),[shareMessage,setShareMessage]=useState("");
 const [sort,setSort]=useState<OpportunitySort>(defaultOpportunitySort),[refresh,setRefresh]=useState(0),[saved,setSaved]=useState<string[]>([]),[saving,setSaving]=useState<string|null>(null),[message,setMessage]=useState("");
 const [selectedOpportunity,setSelectedOpportunity]=useState<Opportunity|null>(null);
 useEffect(()=>{
  if(compact || marketId)return;
  const fromUrl=()=>{const state=readOpportunitySearch(new URLSearchParams(window.location.search));setFilters(state.filters);setSort(state.sort);};
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
  try{await navigator.clipboard.writeText(url.href);setShareMessage("Search link copied.");}
  catch{setShareMessage("Unable to copy automatically. Copy the address from your browser.");}
 }
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
 const visible=sortOpportunities(filterOpportunities(items,filters),sort);
 const unconfirmedCount=filters.category ? visible.filter(item=>opportunityCategoryStatus(item,filters.category)==="unknown").length : 0;
 const input="mt-2 w-full min-w-0 border border-[#252521]/25 bg-[#FFFCF6] px-3 py-3 text-sm outline-none focus:border-[#07472B]";
 return <div>
 {!compact&&<div className="mt-6 border-y border-[#252521]/20 py-4"><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
 <label className="text-xs font-bold text-[#626C57]">SEARCH MARKETS OR ORGANIZERS<input className={input} value={filters.search} onChange={event=>setFilters({...filters,search:event.target.value})} placeholder="Market, organizer, city, or venue…"/></label>
 <label className="text-xs font-bold text-[#626C57]">LOCATION<select className={input} value={filters.city} onChange={event=>setFilters({...filters,city:event.target.value})}><option value="">All locations</option>{[...new Set(items.map(item=>item.city))].sort().map(city=><option key={city}>{city}</option>)}</select></label>
 <label className="text-xs font-bold text-[#626C57]">EVENT MONTH<input type="month" className={input} value={filters.month} onChange={event=>setFilters({...filters,month:event.target.value})}/></label>
 <label className="text-xs font-bold text-[#626C57]">VENDOR CATEGORY<select className={input} value={filters.category} onChange={event=>setFilters({...filters,category:event.target.value})}><option value="">All categories</option>{VENDOR_CATEGORIES.map(category=><option key={category}>{category}</option>)}</select></label>
 <label className="text-xs font-bold text-[#626C57]">OPPORTUNITY TYPE<select className={input} value={filters.schedule ?? "all"} onChange={event=>setFilters({...filters,schedule:event.target.value as "all" | "dated" | "seasonal" | "ongoing"})}><option value="all">All opportunities</option><option value="dated">Dated events</option><option value="seasonal">Seasonal applications / waitlists</option><option value="ongoing">Ongoing / rolling applications</option></select></label>
 <label className="text-xs font-bold text-[#626C57]">APPLICATION STATUS<select className={input} value={filters.status} onChange={event=>setFilters({...filters,status:event.target.value})}><option value="active">Open, limited or waitlist</option>{["all","open","limited","waitlist","needs_recheck","closed"].map(status=><option key={status} value={status}>{status==="all"?"All statuses":statusLabel(status)}</option>)}</select></label>
 <label className="text-xs font-bold text-[#626C57]">SORT<select className={input} value={sort} onChange={event=>setSort(event.target.value as OpportunitySort)}><option value="date">Upcoming event date</option><option value="deadline">Application deadline (confirmed first)</option><option value="fee_asc">Booth fee (lowest published first)</option><option value="rating_desc">Vendor rating (reviewed first)</option></select></label>
 </div>
 <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
 <label className="text-xs font-bold text-[#626C57]">BOOTH PRICE<select className={input} value={filters.priceAvailability} onChange={event=>setFilters({...filters,priceAvailability:event.target.value as "all" | "published" | "unpublished"})}><option value="all">All prices</option><option value="published">Published prices only</option><option value="unpublished">Price not published</option></select></label>
 <label className="text-xs font-bold text-[#626C57]">MAXIMUM PUBLISHED BOOTH FEE ($)<input className={input} type="number" min="0" step="1" inputMode="numeric" value={filters.maxBoothFee} onChange={event=>setFilters({...filters,maxBoothFee:event.target.value,priceAvailability:event.target.value?"all":filters.priceAvailability})} placeholder="No maximum" /></label>
 <label className="text-xs font-bold text-[#626C57]">APPLICATION DEADLINE ON OR BEFORE<input className={input} type="date" value={filters.deadlineBefore} onChange={event=>setFilters({...filters,deadlineBefore:event.target.value})}/></label>
 </div>
 {(filters.maxBoothFee || filters.deadlineBefore || sort==="fee_asc" || sort==="rating_desc")&&<p className="mt-3 text-xs leading-relaxed text-[#626C57]">Fee filters use only published standard booth prices; unknown prices are not treated as free. Deadline filtering uses confirmed event-specific cutoffs only. Unreviewed markets appear last when sorting by rating.</p>}
 {filters.category&&<div className="mt-4"><label className="flex min-h-11 items-center gap-3 text-sm"><input type="checkbox" checked={filters.includeUnconfirmed} onChange={event=>setFilters({...filters,includeUnconfirmed:event.target.checked})} aria-describedby="unconfirmed-category-help"/>Include opportunities with unconfirmed categories</label><p id="unconfirmed-category-help" className="text-xs leading-relaxed text-[#626C57]">Unconfirmed listings may accept your category; check with the organizer. They are not confirmed matches.</p></div>}
 <div className="mt-3 flex flex-wrap items-center justify-between gap-3"><p role="status" className="text-sm text-[#55554E]">{loading?"Checking opportunities…":`${visible.length} ${visible.length===1?"opportunity":"opportunities"}${unconfirmedCount?` · ${unconfirmedCount} with unconfirmed categories`:""}`}</p><div className="flex flex-wrap gap-x-5"><button type="button" onClick={()=>void copySearchLink()} className="min-h-11 text-sm font-semibold text-[#07472B] underline">Copy search link</button><button type="button" onClick={()=>{setFilters({...defaultOpportunityFilters});setSort(defaultOpportunitySort);}} className="min-h-11 text-sm font-semibold text-[#07472B] underline">Clear filters</button>{filters.status!=="all"&&<button type="button" onClick={()=>setFilters({...filters,status:"all"})} className="min-h-11 text-sm font-semibold text-[#07472B] underline">Show all statuses</button>}</div></div>{shareMessage&&<p role="status" className="mt-2 text-xs text-[#07472B]">{shareMessage}</p>}</div>}
 {!compact&&sort==="deadline"&&<p className="mt-3 text-xs leading-relaxed text-[#626C57]">Event-specific deadlines appear first. Series deadlines and unconfirmed cutoffs appear afterward, ordered by event date.</p>}
 {message&&<p role="status" className="my-5 border-l-2 border-[#07472B] bg-[#E9E7DA] p-4 text-sm">{message} <Link href="/login" className="font-semibold underline">My Account →</Link></p>}
 {error?<div role="alert" className="mt-6"><p>{error}</p><button onClick={()=>setRefresh(value=>value+1)} className="mt-3 font-semibold underline">Refresh opportunities</button></div>:loading?<p role="status" className="mt-6">Loading opportunities…</p>:visible.length===0?<p className="mt-6 text-[#55554E]">{compact?"No recently verified vendor applications or waitlists are listed for this market right now.":"No opportunities match these filters. Try another location or month, include unconfirmed categories, or show all statuses."}</p>:<div className={`mt-5 grid items-stretch gap-5 ${compact?"":"md:grid-cols-2 lg:grid-cols-3"}`}>
 {(compact?visible.slice(0,3):visible).map(item=><OpportunityCard
   key={item.id}
   item={item}
   categoryFilter={filters.category}
   saved={saved.includes(item.id)}
   saving={saving!==null}
   onSave={()=>void toggle(item.id)}
   onViewDetails={()=>setSelectedOpportunity(item)}
 />)}
 </div>}
 {selectedOpportunity&&<OpportunityDetailsDialog item={selectedOpportunity} onClose={()=>setSelectedOpportunity(null)} />}
 </div>;
}
