"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { createClient } from "../lib/supabase/client";
import { safeExternalUrl } from "../lib/opportunities";
import { formatAttendanceDate } from "../lib/attendanceDate";

type Draft = { application_url: string; source_url: string; resource_kind: string; public_note: string; private_notes: string; published: boolean };
type Saved = Draft & { revision: string; checked_on: string };
const blank: Draft = { application_url: "", source_url: "", resource_kind: "information", public_note: "", private_notes: "", published: false };
const input = "mt-2 w-full rounded-sm border border-[#252521]/25 bg-[#FFFCF6] px-3 py-2.5 text-sm outline-none focus:border-[#07472B]";
function draftOf(row: Saved | null): Draft { return row ? { application_url: row.application_url, source_url: row.source_url, resource_kind: row.resource_kind, public_note: row.public_note, private_notes: row.private_notes, published: row.published } : { ...blank }; }
export default function MarketVendorApplicationEditor({ marketId, onDirtyChange }: { marketId: string; onDirtyChange: (dirty: boolean) => void }) {
  const [saved,setSaved] = useState<Saved | null>(null);
  const [draft,setDraft] = useState<Draft>({ ...blank });
  const [loading,setLoading] = useState(true), [busy,setBusy] = useState(false), [confirmed,setConfirmed] = useState(false), [error,setError] = useState(""), [message,setMessage] = useState("");
  const active = useRef(true);
  const loadVersion = useRef(0);
  const dirty = JSON.stringify(draft) !== JSON.stringify(draftOf(saved));
  async function load() {
    const version=++loadVersion.current;
    const { data,error } = await createClient().rpc("btb_admin_market_vendor_application", { p_market_id: marketId });
    if (error) throw error;
    if (active.current && version===loadVersion.current) { setSaved(data); setDraft(draftOf(data)); setConfirmed(false); setError(""); }
  }
  useEffect(() => {
    active.current = true;
    void load().catch(() => { if(active.current)setError("Unable to load this market’s application information. Check the SQL update and admin sign-in."); }).finally(() => { if(active.current)setLoading(false); });
    return () => { active.current = false; loadVersion.current++; onDirtyChange(false); };
  }, [marketId]); // Parent keys this component by market ID.
  useEffect(() => { onDirtyChange(dirty||busy); }, [dirty,busy,onDirtyChange]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload",warn);return () => window.removeEventListener("beforeunload",warn);
  },[dirty]);
  function update<K extends keyof Draft>(key: K,value: Draft[K]) { setDraft(current => ({ ...current,[key]:value }));setConfirmed(false);setMessage(""); }
  async function save(event: FormEvent) {
    event.preventDefault();if(busy)return;setError("");setMessage("");
    const application = safeExternalUrl(draft.application_url.trim()), source = safeExternalUrl(draft.source_url.trim());
    if(!application || !source){setError("Enter complete HTTPS application-information and source URLs without embedded login details.");return;}
    if((draft.published || !saved) && !confirmed){setError("Check the official source and confirm verification before saving.");return;}
    setBusy(true);
    try {
      const { error } = await createClient().rpc("btb_admin_save_market_vendor_application", { p_market_id: marketId,p_data:{ ...draft,application_url:application,source_url:source },p_expected_revision:saved?.revision??null,p_confirm_verified:confirmed });
      if(error)throw error;
      await load();if(active.current)setMessage("Application information saved. Refresh the public market profile to view it.");
    } catch(cause) { if(active.current)setError((cause as { message?:string })?.message??"Unable to save application information."); }
    finally { if(active.current)setBusy(false); }
  }
  return <section className="mt-8 border-t border-[#252521]/20 pt-8">
    <h3 className="font-serif text-2xl font-bold">General vendor application information</h3>
    <p className="mt-3 text-sm leading-relaxed text-[#55554E]">A permanent general/seasonal resource for this market, separate from dated opportunities and their availability. Saving a URL does not publish an upcoming event or mark applications open.</p>
    {loading?<p role="status" className="mt-4 text-sm">Loading application information…</p>:<form onSubmit={save} className="mt-5"><fieldset disabled={busy} className="min-w-0 space-y-4">
      <label className="block text-sm font-semibold">Official vendor application / information URL<input required type="url" maxLength={1500} className={input} value={draft.application_url} onChange={event=>update("application_url",event.target.value)}/></label>
      <label className="block text-sm font-semibold">Official verification source URL<input required type="url" maxLength={1500} className={input} value={draft.source_url} onChange={event=>update("source_url",event.target.value)}/></label>
      <label className="block text-sm font-semibold">Resource type<select className={input} value={draft.resource_kind} onChange={event=>update("resource_kind",event.target.value)}><option value="information">General / seasonal vendor information</option><option value="application">Application form / application portal</option><option value="interest">Vendor interest / notification information</option></select></label>
      <label className="block text-sm font-semibold">Public note<textarea rows={3} maxLength={1200} className={input} value={draft.public_note} onChange={event=>update("public_note",event.target.value)}/></label>
      <label className="block text-sm font-semibold">Private research notes<textarea rows={3} maxLength={2500} className={input} value={draft.private_notes} onChange={event=>update("private_notes",event.target.value)}/></label>
      <label className="flex items-start gap-3 text-sm"><input type="checkbox" className="mt-1" checked={draft.published} onChange={event=>update("published",event.target.checked)}/>Show this resource on the public market profile. Uncheck to hide an incorrect or outdated link.</label>
      <label className="flex items-start gap-3 text-sm"><input type="checkbox" className="mt-1" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/>I opened the official source and verified this link belongs to this market. This updates its last-checked date.</label>
      {saved&&<p className="text-xs text-[#626C57]">Last checked: {formatAttendanceDate(saved.checked_on)}</p>}
      <div className="flex flex-wrap gap-4"><button type="submit" className="heritage-button disabled:opacity-50">{busy?"Saving…":"Save application information"}</button><button type="button" onClick={()=>{setDraft(draftOf(saved));setConfirmed(false);setError("");}} className="text-sm font-semibold text-[#07472B] underline">Discard link changes</button><button type="button" onClick={()=>void load().catch(()=>setError("Unable to reload application information."))} className="text-sm font-semibold text-[#07472B] underline">Reload saved link</button></div>
    </fieldset></form>}
    {error&&<p role="alert" className="mt-4 text-sm">{error}</p>}{message&&<p role="status" className="mt-4 text-sm">{message}</p>}
  </section>;
}
