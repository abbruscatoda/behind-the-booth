"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { createClient } from "../../../lib/supabase/client";

type Market = {
  id: string; slug: string; name: string; city: string; state: string;
  description: string; website_url: string | null; is_sample: boolean; revision: string;
};
type Draft = { name: string; city: string; state: string; description: string; website: string };
type Results = { items: Market[]; total: number };
const inputStyle = "mt-2 w-full rounded-sm border border-[#252521]/25 bg-[#FFFCF6] px-3 py-2.5 text-sm outline-none focus:border-[#07472B] disabled:opacity-60";
const buttonStyle = "inline-flex items-center justify-center rounded-sm border border-[#07472B]/40 px-4 py-2.5 text-sm font-semibold text-[#07472B] hover:bg-[#E9E7DA] disabled:cursor-not-allowed disabled:opacity-50";
function draftOf(market: Market): Draft { return { name: market.name, city: market.city, state: market.state, description: market.description, website: market.website_url ?? "" }; }
function clean(draft: Draft): Draft { return { name: draft.name.trim(), city: draft.city.trim(), state: draft.state.trim().toUpperCase(), description: draft.description.trim(), website: draft.website.trim() }; }
function errorMessage(value: unknown) {
  if (typeof value === "object" && value !== null && "message" in value && typeof value.message === "string") return value.message;
  return "Something went wrong. Please try again.";
}
function validWebsite(value: string) {
  if (!value) return true;
  try {
    const url = new URL(value);
    return /^https?:\/\//.test(value) && ["https:", "http:"].includes(url.protocol) && Boolean(url.hostname) && !url.username && !url.password && !/[\s@]/.test(value);
  } catch { return false; }
}
function Field({ label, children }: { label: string; children: ReactNode }) { return <label className="block text-sm font-semibold">{label}{children}</label>; }
const fields: { label: string; key: keyof Draft }[] = [
  { label: "Market name", key: "name" }, { label: "City", key: "city" },
  { label: "State", key: "state" }, { label: "Website", key: "website" },
  { label: "Description", key: "description" },
];

export default function ManageMarketsPage() {
  const [userId, setUserId] = useState<string | null>(null);
  const identity = useRef<string | null>(null);
  const [checking, setChecking] = useState(true);
  const [accessChecking, setAccessChecking] = useState(false);
  const [allowedOwner, setAllowedOwner] = useState<string | null>(null);
  const [accessError, setAccessError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [results, setResults] = useState<Results | null>(null);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [selected, setSelected] = useState<Market | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [preview, setPreview] = useState<Draft | null>(null);
  const [saveError, setSaveError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const saving = useRef(false);
  const allowed = Boolean(userId && allowedOwner === userId);
  const dirty = Boolean(selected && draft && JSON.stringify(clean(draft)) !== JSON.stringify(draftOf(selected)));
  const locked = busy || dirty || Boolean(preview);

  useEffect(() => {
    let active = true;
    let authChanged = false;
    const supabase = createClient();
    function accept(id: string | null) {
      if (!active) return;
      if (identity.current !== id) {
        identity.current = id;
        setUserId(id); setAllowedOwner(null); setAccessChecking(Boolean(id));
        setResults(null); setSelected(null); setDraft(null); setPreview(null);
        setSaveError(""); setSuccess(""); setListError(""); setAccessError("");
      }
      setChecking(false);
    }
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      authChanged = true; accept(session?.user.id ?? null);
    });
    void supabase.auth.getUser().then(({ data, error }) => {
      if (active && !authChanged) {
        accept(data.user?.id ?? null);
        if (error && error.name !== "AuthSessionMissingError") setAccessError(errorMessage(error));
      }
    }).catch(error => { if (active && !authChanged) { accept(null); setAccessError(errorMessage(error)); } });
    return () => { active = false; subscription.unsubscribe(); };
  }, []);

  useEffect(() => {
    if (!userId) return;
    let active = true;
    setAccessChecking(true); setAccessError("");
    void (async () => {
      try {
        const { data, error } = await createClient().rpc("btb_is_admin");
        if (error) throw error;
        if (active && identity.current === userId) setAllowedOwner(data === true ? userId : null);
      } catch (error) {
        if (active && identity.current === userId) { setAllowedOwner(null); setAccessError(errorMessage(error)); }
      } finally { if (active && identity.current === userId) setAccessChecking(false); }
    })();
    return () => { active = false; };
  }, [userId, refresh]);

  useEffect(() => {
    if (!allowed || !userId) return;
    let active = true;
    setLoading(true); setListError(""); setResults(null);
    void (async () => {
      try {
        const { data, error } = await createClient().rpc("btb_admin_markets", { p_search: search, p_offset: offset });
        if (error) throw error;
        if (active && identity.current === userId) {
          const list = data as Results;
          if (offset > 0 && list.items.length === 0) setOffset(Math.max(0, offset - 20));
          else setResults(list);
        }
      } catch (error) { if (active && identity.current === userId) setListError(errorMessage(error)); }
      finally { if (active && identity.current === userId) setLoading(false); }
    })();
    return () => { active = false; };
  }, [allowed, userId, search, offset, refresh]);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  function choose(market: Market) {
    setSelected(market); setDraft(draftOf(market)); setPreview(null); setSaveError(""); setSuccess("");
  }
  function update(key: keyof Draft, value: string) { setDraft(current => current ? { ...current, [key]: value } : current); setSaveError(""); }
  function runSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked) return;
    setSelected(null); setDraft(null); setSuccess(""); setSaveError("");
    setSearch(searchInput.trim()); setOffset(0); setRefresh(n => n + 1);
  }
  function reviewChanges(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft || !selected || !dirty) return;
    const next = clean(draft);
    if (!next.name || !next.city || !/^[A-Z]{2}$/.test(next.state) || !next.description || !validWebsite(next.website)) {
      setSaveError("Enter a market name, city, two-letter state, and description. Website links must start with http:// or https:// and contain no spaces or embedded login details."); return;
    }
    setSaveError(""); setPreview(next);
  }
  async function save() {
    if (!preview || !selected || !allowed || !userId || saving.current) return;
    const actor = userId;
    const market = selected;
    const next = preview;
    saving.current = true; setBusy(true); setSaveError(""); setSuccess("");
    try {
      const supabase = createClient();
      const { data: authData, error: authError } = await supabase.auth.getUser();
      if (authError) throw authError;
      if (authData.user?.id !== actor || identity.current !== actor) throw new Error("Your signed-in account changed. Reload before saving.");
      const { data, error } = await supabase.rpc("btb_admin_update_market", {
        p_id: market.id, p_revision: market.revision, p_name: next.name,
        p_city: next.city, p_state: next.state, p_description: next.description,
        p_website_url: next.website || null,
      });
      if (error) throw error;
      if (identity.current !== actor) return;
      const updated = data as Market;
      setSelected(updated); setDraft(draftOf(updated)); setPreview(null);
      setSuccess("Market updated. Its URL and existing reviews are still connected.");
      setRefresh(n => n + 1);
    } catch (error) { if (identity.current === actor) setSaveError(errorMessage(error)); }
    finally { saving.current = false; setBusy(false); }
  }
  function reloadDirectory() {
    if (busy) return;
    setSelected(null); setDraft(null); setPreview(null); setSaveError(""); setSuccess(""); setRefresh(n => n + 1);
  }

  return <main className="mx-auto min-h-[65vh] max-w-6xl px-6 py-10 md:py-14">
    <p className="heritage-label">The market directory</p>
    <h1 className="heritage-heading mt-4 text-4xl md:text-5xl">Manage Markets.</h1>
    <p className="mt-4 max-w-3xl leading-relaxed text-[#55554E]">Keep existing listings accurate. Update their public details, review your changes, and save them here.</p>
    {checking || (userId && accessChecking && !allowed) ? <p role="status" className="mt-8">Checking admin access…</p>
      : !userId ? <section className="heritage-card mt-8"><h2 className="font-serif text-2xl font-bold">Sign in to continue.</h2><p className="mt-3 text-[#55554E]">Use your existing administrator account, then return to this page.</p><Link href="/login" className="heritage-button mt-5">Sign in →</Link>{accessError && <p role="alert" className="mt-4 text-sm text-[#9B3E35]">{accessError}</p>}</section>
      : !allowed ? <section className="heritage-card mt-8"><h2 className="font-serif text-2xl font-bold">{accessError ? "Unable to check access" : "Admin access required"}</h2><p className="mt-3 break-words text-[#55554E]">{accessError || "This account cannot edit market listings."}</p><div className="mt-5 flex flex-wrap gap-3"><Link href="/login" className={buttonStyle}>My Account / switch account</Link><button type="button" className={buttonStyle} onClick={() => setRefresh(n => n + 1)}>Try again</button></div></section>
      : <>
        <form onSubmit={runSearch} className="mt-8 flex flex-wrap items-end gap-3">
          <div className="min-w-0 flex-1 basis-64"><Field label="Search market name, city, or state"><input type="search" value={searchInput} maxLength={150} onChange={e => setSearchInput(e.target.value)} disabled={busy || Boolean(preview)} className={inputStyle} placeholder="Try Cary, Raleigh, or a market name" /></Field></div>
          <button type="submit" className={buttonStyle} disabled={locked || loading}>Search</button>
          <button type="button" className={buttonStyle} disabled={locked || loading} onClick={reloadDirectory}>Refresh</button>
        </form>
        {dirty && <p role="status" className="mt-3 text-sm text-[#80621A]">You have unsaved changes. Save or discard them before choosing another listing or searching.</p>}
        {success && <div role="status" className="mt-5 border-l-2 border-[#07472B] bg-[#E9E7DA] p-4 text-sm">{success} {selected && <Link href={`/markets/${selected.slug}`} target="_blank" rel="noopener noreferrer" className="font-semibold underline underline-offset-4">View updated listing ↗</Link>}</div>}
        {listError && <div role="alert" className="mt-5 break-words border-l-2 border-[#9B3E35] bg-[#F0E3DA] p-4 text-sm text-[#9B3E35]">Could not load the directory: {listError}</div>}
        <div className="mt-6 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.7fr)]">
          <section aria-label="Market listings" className="min-w-0 rounded-sm border border-[#252521]/20 bg-[#FFFCF6]">
            <div className="border-b border-[#252521]/15 px-5 py-4"><h2 className="font-serif text-xl font-bold">Find a listing</h2>{results && <p className="mt-1 text-xs text-[#626C57]">{results.total} {results.total === 1 ? "market" : "markets"} found</p>}</div>
            {loading ? <p role="status" className="p-5 text-sm">Loading markets…</p> : !results ? <p className="p-5 text-sm text-[#626C57]">Use Refresh to load the directory.</p> : !results.items.length ? <p className="p-5 text-sm text-[#626C57]">No matching markets. Try a shorter name or another city.</p> : <ul className="divide-y divide-[#252521]/10">{results.items.map(market => <li key={market.id}><button type="button" disabled={locked} aria-pressed={selected?.id === market.id} onClick={() => choose(market)} className={`w-full px-5 py-4 text-left transition disabled:cursor-not-allowed disabled:opacity-60 ${selected?.id === market.id ? "border-l-4 border-[#07472B] bg-[#E9E7DA]" : "hover:bg-[#F4F0E6]"}`}><span className="block break-words text-sm font-bold">{market.name}</span><span className="mt-1 block text-xs text-[#626C57]">{market.city}, {market.state}{market.is_sample ? " · Demonstration" : ""}</span></button></li>)}</ul>}
            {results && results.total > 20 && <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#252521]/15 p-4 text-xs"><span>{offset + 1}–{Math.min(offset + 20, results.total)} of {results.total}</span><div className="flex gap-2"><button type="button" className={buttonStyle} disabled={locked || !offset} onClick={() => { setSelected(null); setDraft(null); setOffset(n => Math.max(0, n - 20)); }}>Previous</button><button type="button" className={buttonStyle} disabled={locked || offset + 20 >= results.total} onClick={() => { setSelected(null); setDraft(null); setOffset(n => n + 20); }}>Next</button></div></div>}
          </section>
          <section aria-label="Market editor" className="min-w-0 rounded-sm border border-[#252521]/20 bg-[#FFFCF6] p-5 md:p-7">
            {!selected || !draft ? <div className="py-8"><p className="heritage-label">Keep the details current</p><h2 className="mt-4 font-serif text-2xl font-bold">Choose a market to edit.</h2><p className="mt-3 text-sm leading-relaxed text-[#55554E]">Select a listing from the directory. You can update its name, location, description, and website.</p></div> : <>
              <h2 className="break-words font-serif text-2xl font-bold">{selected.name}</h2>
              <p className="mt-2 break-all text-xs text-[#626C57]">Permanent URL: /markets/{selected.slug}</p>
              <Link href={`/markets/${selected.slug}`} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block text-sm font-semibold text-[#07472B] underline underline-offset-4">View current public listing ↗</Link>
              {selected.is_sample && <p className="mt-4 border-l-2 border-[#AD573B] bg-[#F4F0E6] p-3 text-sm">This is a demonstration market. Its sample label stays in place.</p>}
              {saveError && <div role="alert" className="mt-5 break-words border-l-2 border-[#9B3E35] bg-[#F0E3DA] p-4 text-sm text-[#9B3E35]">{saveError}<p className="mt-2">If the listing changed elsewhere or the connection was interrupted, reload the latest listing before retrying. Reloading discards this draft.</p><button type="button" disabled={busy} className={`${buttonStyle} mt-3`} onClick={reloadDirectory}>Discard draft & reload directory</button></div>}
              {preview ? <div className="mt-6">
                <p className="heritage-label">Review before saving</p><h3 className="mt-3 font-serif text-2xl font-bold">Confirm your changes.</h3><p className="mt-2 text-sm leading-relaxed text-[#55554E]">Only the fields below will change. The market URL and its reviews stay connected.</p>
                <dl className="mt-5 divide-y divide-[#252521]/15">{fields.filter(field => draftOf(selected)[field.key] !== preview[field.key]).map(field => <div key={field.key} className="py-4"><dt className="text-xs font-bold uppercase tracking-wider text-[#07472B]">{field.label}</dt><dd className="mt-2 grid min-w-0 gap-3 sm:grid-cols-2"><div className="min-w-0 bg-[#F4F0E6] p-3"><p className="text-xs font-semibold text-[#626C57]">Current</p><p className="mt-2 whitespace-pre-wrap break-words text-sm">{draftOf(selected)[field.key] || "No website supplied"}</p></div><div className="min-w-0 border-l-2 border-[#07472B] bg-[#E9E7DA] p-3"><p className="text-xs font-semibold text-[#07472B]">After saving</p><p className="mt-2 whitespace-pre-wrap break-words text-sm">{preview[field.key] || "No website supplied"}</p></div></dd></div>)}</dl>
                <div className="mt-5 flex flex-wrap gap-3"><button type="button" disabled={busy} onClick={() => void save()} className="heritage-button disabled:opacity-50">{busy ? "Saving…" : "Confirm & save changes"}</button><button type="button" disabled={busy} className={buttonStyle} onClick={() => { setPreview(null); setSaveError(""); }}>Back to editing</button></div>
              </div> : <form onSubmit={reviewChanges} className="mt-6">
                <fieldset disabled={busy} className="grid min-w-0 gap-4 sm:grid-cols-2">
                  <div className="sm:col-span-2"><Field label="Market name"><input value={draft.name} maxLength={150} required className={inputStyle} onChange={e => update("name", e.target.value)} /></Field></div>
                  <Field label="City"><input value={draft.city} maxLength={100} required className={inputStyle} onChange={e => update("city", e.target.value)} /></Field>
                  <Field label="State"><input value={draft.state} maxLength={2} required className={inputStyle} onChange={e => update("state", e.target.value.toUpperCase())} /></Field>
                  <div className="sm:col-span-2"><Field label="Official website / event link (optional)"><input type="url" value={draft.website} maxLength={1000} className={inputStyle} onChange={e => update("website", e.target.value)} placeholder="https://" /></Field><p className="mt-1 text-xs text-[#626C57]">Leave blank if no official link is available.</p></div>
                  <div className="sm:col-span-2"><Field label="Public description"><textarea value={draft.description} rows={6} maxLength={2000} required className={inputStyle} onChange={e => update("description", e.target.value)} /></Field><p className="mt-1 text-xs leading-relaxed text-[#626C57]">Use neutral, verified facts. Leave subjective experiences to vendor reviews.</p></div>
                  <div className="flex flex-wrap gap-3 sm:col-span-2"><button type="submit" disabled={!dirty} className="heritage-button disabled:opacity-50">Review changes →</button><button type="button" disabled={!dirty} className={buttonStyle} onClick={() => { setDraft(draftOf(selected)); setSaveError(""); }}>Discard changes</button></div>
                </fieldset>
              </form>}
            </>}
          </section>
        </div>
      </>}
  </main>;
}
