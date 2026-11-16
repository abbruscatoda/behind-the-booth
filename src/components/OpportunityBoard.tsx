"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { createClient } from "../lib/supabase/client";
import { formatAttendanceDate } from "../lib/attendanceDate";
import { filterOpportunities, fee, safeExternalUrl, statusLabel, VENDOR_CATEGORIES, type Opportunity } from "../lib/opportunities";

export default function OpportunityBoard({ marketId, compact = false }: { marketId?: string; compact?: boolean }) {
 const [items,setItems]=useState<Opportunity[]>([]), [loading,setLoading]=useState(true), [error,setError]=useState("");
 const [filters,setFilters]=useState({search:"",city:"",month:"",category:"",status:"active"});
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
 const visible=filterOpportunities(items,filters).sort((a,b)=>sort==="deadline"?(a.deadline?Date.parse(a.deadline):Infinity)-(b.deadline?Date.parse(b.deadline):Infinity):a.starts_on.localeCompare(b.starts_on));
 const input="mt-2 w-full min-w-0 border border-[#252521]/25 bg-[#FFFCF6] px-3 py-3 text-sm outline-none focus:border-[#07472B]";
 return <div>
 {!compact&&<div className="mt-8 border-y border-[#252521]/20 py-6"><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
 <label className="text-xs font-bold text-[#626C57]">SEARCH MARKETS OR ORGANIZERS<input className={input} value={filters.search} onChange={event=>setFilters({...filters,search:event.target.value})} placeholder="Search opportunities…"/></label>
 <label className="text-xs font-bold text-[#626C57]">LOCATION<select className={input} value={filters.city} onChange={event=>setFilters({...filters,city:event.target.value})}><option value="">All locations</option>{[...new Set(items.map(item=>item.city))].sort().map(city=><option key={city}>{city}</option>)}</select></label>
 <label className="text-xs font-bold text-[#626C57]">EVENT MONTH<input type="month" className={input} value={filters.month} onChange={event=>setFilters({...filters,month:event.target.value})}/></label>
 <label className="text-xs font-bold text-[#626C57]">VENDOR CATEGORY<select className={input} value={filters.category} onChange={event=>setFilters({...filters,category:event.target.value})}><option value="">All categories</option>{VENDOR_CATEGORIES.map(category=><option key={category}>{category}</option>)}</select></label>
 <label className="text-xs font-bold text-[#626C57]">APPLICATION STATUS<select className={input} value={filters.status} onChange={event=>setFilters({...filters,status:event.target.value})}><option value="active">Open or limited</option>{["all","open","limited","waitlist","needs_recheck","closed"].map(status=><option key={status} value={status}>{status==="all"?"All statuses":statusLabel(status)}</option>)}</select></label>
 <label className="text-xs font-bold text-[#626C57]">SORT<select className={input} value={sort} onChange={event=>setSort(event.target.value)}><option value="date">Upcoming event date</option><option value="deadline">Application deadline</option></select></label>
 </div><div className="mt-4 flex flex-wrap justify-between gap-4"><p role="status" className="text-sm text-[#55554E]">{loading?"Checking opportunities…":`${visible.length} matching opportunities`}</p><button type="button" onClick={()=>setFilters({search:"",city:"",month:"",category:"",status:"all"})} className="text-sm font-semibold text-[#07472B] underline">Clear filters / show all statuses</button></div></div>}
 {message&&<p role="status" className="my-5 border-l-2 border-[#07472B] bg-[#E9E7DA] p-4 text-sm">{message} <Link href="/login" className="font-semibold underline">My Account →</Link></p>}
 {error?<div role="alert" className="mt-6"><p>{error}</p><button onClick={()=>setRefresh(value=>value+1)} className="mt-3 font-semibold underline">Refresh opportunities</button></div>:loading?<p role="status" className="mt-6">Loading opportunities…</p>:visible.length===0?<p className="mt-6 text-[#55554E]">{compact?"No recently verified open applications are listed for this market right now.":"No opportunities match these filters. Try another month or include waitlisted and unverified listings."}</p>:<div className={`mt-8 grid gap-6 ${compact?"":"lg:grid-cols-2"}`}>
 {(compact?visible.slice(0,3):visible).map(item=><article key={item.id} id={item.id} className="heritage-card scroll-mt-8 flex flex-col">
 <div className="flex flex-wrap items-center justify-between gap-3"><p className="heritage-label">{statusLabel(item.effective_status)}</p><p className="text-xs text-[#626C57]">{item.verified_at?`Checked ${new Date(item.verified_at).toLocaleDateString("en-US",{timeZone:"America/New_York"})}`:"Not verified"}</p></div>
 <h2 className="mt-5 font-serif text-3xl font-bold">{item.title}</h2><p className="mt-3 text-sm font-semibold text-[#07472B]">{item.organizer}</p>
 <p className="mt-3 text-sm leading-relaxed">{item.venue} · {item.city}, {item.state}<br/>{formatAttendanceDate(item.starts_on)}{item.ends_on!==item.starts_on?` – ${formatAttendanceDate(item.ends_on)}`:""}</p>
 <p className="mt-4 text-sm"><strong>Apply by:</strong> {item.deadline?new Date(item.deadline).toLocaleString("en-US",{timeZone:"America/New_York",dateStyle:"medium",timeStyle:"short"})+" Eastern":"Deadline not published"}</p>
 <p className="mt-3 text-sm"><strong>Categories:</strong> {item.categories.join(", ")||"Confirm with organizer"}</p>
 <dl className="mt-5 grid grid-cols-3 gap-3 border-y border-[#252521]/15 py-4 text-sm"><div><dt className="text-xs text-[#626C57]">Booth / table</dt><dd>{fee(item.booth_fee)}</dd></div><div><dt className="text-xs text-[#626C57]">Application fee</dt><dd>{fee(item.application_fee)}</dd></div><div><dt className="text-xs text-[#626C57]">Deposit</dt><dd>{fee(item.deposit)}</dd></div></dl>
 {item.fee_notes&&<p className="mt-3 whitespace-pre-wrap text-xs leading-relaxed text-[#626C57]">{item.fee_notes}</p>}{item.eligibility&&<p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed">{item.eligibility}</p>}
 <div className="mt-5 border-l-2 border-[#07472B] bg-[#E9E7DA] p-4 text-sm"><Link href={`/markets/${item.market_slug}#vendor-reviews`} className="font-semibold text-[#07472B] underline">Read past vendor reviews →</Link><p className="mt-2 text-xs">{item.history.review_count?`${item.history.overall}/5 · ${item.history.review_count} reviews from ${item.history.reviewer_count} vendors`:"No approved reviews yet"}. Past market experiences—not a rating of this upcoming date.</p></div>
 <div className="mt-6 flex flex-wrap items-center gap-5">{["open","limited","waitlist"].includes(item.effective_status)&&safeExternalUrl(item.application_url)?<a href={safeExternalUrl(item.application_url)!} target="_blank" rel="noopener noreferrer" className="heritage-button">{item.effective_status==="waitlist"?"Official waitlist":"Official application"} ↗</a>:<span className="text-sm text-[#626C57]">{item.effective_status==="closed"?"Application closed":"Recheck with organizer before applying"}</span>}<button disabled={saving!==null} onClick={()=>void toggle(item.id)} className="min-h-11 text-sm font-semibold text-[#07472B] underline disabled:opacity-50">{saved.includes(item.id)?"Saved — remove":"Save opportunity"}</button>{safeExternalUrl(item.source_url)&&<a href={safeExternalUrl(item.source_url)!} target="_blank" rel="noopener noreferrer" className="text-xs text-[#626C57] underline">Source ↗</a>}</div>
 </article>)}
 </div>}
 </div>;
}
