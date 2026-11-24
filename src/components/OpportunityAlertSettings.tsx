"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { createClient } from "../lib/supabase/client";
import { VENDOR_CATEGORIES } from "../lib/opportunities";

type Preferences = {
  new_matches: boolean; deadline_reminders: boolean; cities: string[];
  categories: string[]; include_unconfirmed: boolean; last_sent_at: string | null;
};
const defaults: Preferences = {new_matches:false, deadline_reminders:false, cities:[], categories:[], include_unconfirmed:false, last_sent_at:null};
const triangleCities = ["Apex","Carrboro","Cary","Chapel Hill","Clayton","Durham","Fuquay-Varina","Garner","Hillsborough","Holly Springs","Knightdale","Morrisville","Pittsboro","Raleigh","Rolesville","Wake Forest","Wendell","Zebulon"];

export default function OpportunityAlertSettings() {
  const [preferences,setPreferences] = useState<Preferences>(defaults);
  const [loading,setLoading] = useState(true);
  const [loadError,setLoadError] = useState("");
  const [error,setError] = useState("");
  const [message,setMessage] = useState("");
  const [busy,setBusy] = useState(false);
  const [refresh,setRefresh] = useState(0);
  const lock = useRef(false);

  useEffect(()=>{
    let active=true;
    async function load(){
      setLoading(true);setLoadError("");
      try {
        const {data,error}=await createClient().rpc("btb_my_opportunity_alerts");
        if(error)throw error;
        if(active)setPreferences(data ?? {...defaults,cities:[],categories:[]});
      }catch{if(active)setLoadError("We couldn't load your email preferences. Try again before making changes.");}
      finally{if(active)setLoading(false);}
    }
    void load();return()=>{active=false;};
  },[refresh]);

  function change<K extends keyof Preferences>(key:K,value:Preferences[K]){
    setPreferences(previous=>({...previous,[key]:value}));setMessage("");setError("");
  }
  function toggle(key:"cities"|"categories",value:string){
    change(key,preferences[key].includes(value)?preferences[key].filter(item=>item!==value):[...preferences[key],value]);
  }
  async function save(event:FormEvent<HTMLFormElement>){
    event.preventDefault();if(lock.current)return;
    lock.current=true;setBusy(true);setMessage("");setError("");
    try{
      const {data,error}=await createClient().rpc("btb_save_opportunity_alerts",{
        p_new_matches:preferences.new_matches,p_deadline_reminders:preferences.deadline_reminders,
        p_cities:preferences.cities,p_categories:preferences.categories,p_include_unconfirmed:preferences.include_unconfirmed,
      });
      if(error)throw error;
      setPreferences(data);
      setMessage(data.new_matches||data.deadline_reminders?"Preferences saved. You'll receive a daily email only when there is something to share.":"Preferences saved. Opportunity emails are off.");
    }catch{setError("Your preferences weren't saved. Your selections are still here; please try again.");}
    finally{lock.current=false;setBusy(false);}
  }
  const locations=[...new Set([...triangleCities,...preferences.cities])].sort();
  return <section id="opportunity-alerts" tabIndex={-1} className="scroll-mt-8 border border-[#252521]/20 bg-[#FFFCF6] p-5 sm:p-6" aria-labelledby="opportunity-alerts-heading">
    <h2 id="opportunity-alerts-heading" className="font-serif text-2xl font-bold">Your opportunity alerts</h2>
    <p className="mt-3 text-sm leading-relaxed text-[#55554E]">Choose what reaches your inbox. These emails are optional and off until you select an option and save. At most one daily digest is sent, only when there are updates. Unsubscribe anytime.</p>
    {loading?<p role="status" className="mt-5 text-sm">Loading email preferences…</p>:loadError?<div className="mt-5"><p role="alert" className="text-sm">{loadError}</p><button type="button" onClick={()=>setRefresh(n=>n+1)} className="mt-3 min-h-11 text-sm font-semibold text-[#07472B] underline">Retry email preferences</button></div>:<form onSubmit={save} className="mt-5">
      <fieldset disabled={busy} className="min-w-0 space-y-4">
        <legend className="sr-only">Optional opportunity email preferences</legend>
        <label className="flex min-h-11 items-start gap-3 text-sm font-semibold"><input type="checkbox" checked={preferences.new_matches} onChange={e=>change("new_matches",e.target.checked)} className="mt-1 size-4 shrink-0 accent-[#07472B]" />Email me new matching opportunities</label>
        {preferences.new_matches&&<div className="space-y-4 border-l-2 border-[#07472B]/25 pl-4">
          <p className="text-sm leading-relaxed text-[#55554E]">Newly published opportunities after you save these preferences. Open applications, limited options, and waitlists can appear; eligibility and placement still require organizer approval.</p>
          <details><summary className="min-h-11 cursor-pointer py-3 text-sm font-semibold text-[#07472B]">Locations · {preferences.cities.length?`${preferences.cities.length} selected`:"All locations"}</summary>
            <p className="mb-2 text-sm text-[#55554E]">Leave every location unchecked for the whole Triangle.</p><div className="grid gap-1 sm:grid-cols-2">{locations.map(city=><label key={city} className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={preferences.cities.includes(city)} onChange={()=>toggle("cities",city)} className="size-4 accent-[#07472B]" />{city}</label>)}</div>
          </details>
          <details><summary className="min-h-11 cursor-pointer py-3 text-sm font-semibold text-[#07472B]">Vendor categories · {preferences.categories.length?`${preferences.categories.length} selected`:"All categories"}</summary>
            <p className="mb-2 text-sm text-[#55554E]">Leave every category unchecked to receive opportunities for any business type. Categories are broad search groups; a match may cover only specific products. Food listings do not confirm beverage or food-truck eligibility.</p><div className="grid gap-1 sm:grid-cols-2">{VENDOR_CATEGORIES.map(category=><label key={category} className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={preferences.categories.includes(category)} onChange={()=>toggle("categories",category)} className="size-4 accent-[#07472B]" />{category}</label>)}</div>
          </details>
          {preferences.categories.length>0&&<label className="flex min-h-11 items-start gap-3 text-sm"><input type="checkbox" checked={preferences.include_unconfirmed} onChange={e=>change("include_unconfirmed",e.target.checked)} className="mt-1 size-4 shrink-0 accent-[#07472B]" /><span>Also include possible matches where my categories are unconfirmed.<span className="mt-1 block text-[#626C57]">Explicitly excluded or unavailable categories are not treated as matches.</span></span></label>}
        </div>}
        <label className="flex min-h-11 items-start gap-3 text-sm font-semibold"><input type="checkbox" checked={preferences.deadline_reminders} onChange={e=>change("deadline_reminders",e.target.checked)} className="mt-1 size-4 shrink-0 accent-[#07472B]" /><span>Remind me about deadlines for saved opportunities<span className="mt-1 block font-normal leading-relaxed text-[#55554E]">One reminder when a confirmed deadline is within three days. Save an opportunity first. Unconfirmed cutoffs cannot generate a reminder.</span></span></label>
        <button type="submit" className="heritage-button min-h-11 w-full disabled:opacity-50 sm:w-auto">{busy?"Saving…":"Save email preferences"}</button>
      </fieldset>
      {preferences.last_sent_at&&<p className="mt-3 text-sm text-[#626C57]">Last digest sent {new Date(preferences.last_sent_at).toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",timeZone:"America/New_York"})}.</p>}
      {message&&<p role="status" className="mt-4 border-l-2 border-[#07472B] bg-[#E9E7DA] p-3 text-sm">{message}</p>}
      {error&&<p role="alert" className="mt-4 border-l-2 border-[#9B3E35] p-3 text-sm text-[#9B3E35]">{error}</p>}
    </form>}
  </section>;
}
