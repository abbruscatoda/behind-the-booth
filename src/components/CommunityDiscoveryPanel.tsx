"use client";
import { useEffect,useState } from "react";
import { createClient } from "../lib/supabase/client";
import { safeExternalUrl } from "../lib/opportunities";

type Source={key:string;organizer:string;city:string;sources:string[];instagram:string[]};
type Lead={id:string;title:string;source_key:string|null;target_url:string;notes:string;state:string;reason:string;last_seen:string;last_checked_at:string|null};
type Report={sources:Source[];leads:Lead[]};

export default function CommunityDiscoveryPanel(){
 const [report,setReport]=useState<Report|null>(null),[error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 useEffect(()=>{let active=true;void createClient().rpc("btb_admin_community_discovery").then(({data,error})=>{if(!active)return;if(error)setError("Community research is temporarily unavailable.");else setReport(data);});return()=>{active=false;};},[]);
 async function refresh(){setBusy(true);const {data,error}=await createClient().rpc("btb_admin_community_discovery");if(error)setError("Community research is temporarily unavailable.");else{setReport(data);setError("");}setBusy(false);}
 return <section className="mt-8 border border-[#252521]/20 bg-[#FFFCF6] p-5 sm:p-6" aria-label="Community and Instagram discovery">
  <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-serif text-2xl font-bold">Community & Instagram research</h2><button type="button" onClick={()=>void refresh()} disabled={busy} className="min-h-11 text-sm font-semibold text-[#07472B] underline disabled:opacity-50">Refresh community research</button></div>
  <p className="mt-2 text-sm leading-relaxed text-[#55554E]">Public organizer posts, venue calendars and vendor reposts widen discovery. A repost or search snippet is a lead; current organizer evidence verifies an opening. Private posts and unreadable pages remain unconfirmed.</p>
  {error&&<p role="status" className="mt-3 text-sm">{error}</p>}
  {report&&<><p className="mt-3 text-sm font-semibold">{report.sources.length} source groups · {report.sources.reduce((n,s)=>n+s.instagram.length,0)} Instagram profiles · {report.leads.length} recent findings</p>
   <details className="mt-3"><summary className="min-h-11 cursor-pointer py-3 font-semibold text-[#07472B]">Monitored organizers and accounts</summary><ul className="grid gap-3 text-sm sm:grid-cols-2">{report.sources.map(source=><li key={source.key}><strong>{source.organizer}</strong> · {source.city}<p className="mt-1 text-xs text-[#626C57]">{source.instagram.map(handle=>`@${handle}`).join(", ")}</p></li>)}</ul></details>
   <details className="mt-3"><summary className="min-h-11 cursor-pointer py-3 font-semibold text-[#07472B]">Recent discovery findings</summary><ul className="space-y-4 text-sm">{report.leads.map(lead=><li key={lead.id} className="border-t border-[#252521]/15 pt-3 [overflow-wrap:anywhere]">{safeExternalUrl(lead.target_url)?<a href={safeExternalUrl(lead.target_url)!} target="_blank" rel="noopener noreferrer" className="font-semibold text-[#07472B] underline">{lead.title}</a>:<strong>{lead.title}</strong>}<span className="ml-2 text-xs text-[#626C57]">{lead.state}</span><p className="mt-1">{lead.reason||"Awaiting current primary-source verification."}</p>{lead.notes&&<p className="mt-1 text-xs leading-relaxed text-[#626C57]">{lead.notes}</p>}<p className="mt-1 text-xs text-[#626C57]">Last seen {new Date(lead.last_seen).toLocaleDateString("en-US",{timeZone:"America/New_York"})}</p></li>)}</ul></details>
  </>}
 </section>;
}
