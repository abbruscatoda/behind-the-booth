"use client";

import Link from "next/link";
import OrganizerField from "../../components/OrganizerField";
import { cleanOrganizer } from "../../lib/marketOrganizers";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { createClient } from "../../lib/supabase/client";
import { getRatingColor } from "../../lib/ratingColors";

type Kind = "suggestions" | "vendors" | "reviews";
type Status = "pending" | "approved" | "rejected" | "duplicate";
import { formatAttendanceDate } from "../../lib/attendanceDate";

type Base = { id: string; status: Status; created_at: string };
type Suggestion = Base & {
  name: string; city: string; state: string; website_url: string;
  organizer: string | null; notes: string | null; linked_market_id: string | null; linked_slug: string | null;
};
type Vendor = Base & {
  business_name: string; business_url: string | null; verification_notes: string;
};
type Review = Base & {
  attended_on: string | null;
  market_name: string; market_slug: string; vendor_categories: string[];
  other_category: string | null; booth_value: number; foot_traffic: number;
  organization: number; promotion: number; overall: number;
  booth_cost: number | null; booth_duration: string | null;
  number_of_days: number | null; experience: string; would_return: string;
};
type Row = Suggestion | Vendor | Review;
type Queue = { items: Row[]; total: number; pending: Record<Kind, number> };
type Market = { id: string; name: string; city: string; state: string; slug: string };
type Listing = { name: string; slug: string; city: string; state: string; description: string; website: string; organizer: string };
type Action =
  | { type: "decide"; kind: Kind; row: Row; status: Status; linkedId?: string }
  | { type: "publish"; row: Suggestion; listing: Listing };

const labels: Record<Kind, string> = { suggestions: "Market suggestions", vendors: "Vendor applications", reviews: "Vendor reviews" };
const inputClass = "mt-2 w-full rounded-sm border border-[#252521]/25 bg-[#FFFCF6] px-3 py-2.5 text-sm outline-none focus:border-[#07472B] disabled:opacity-60";
const secondaryClass = "rounded-sm border border-[#07472B]/40 px-4 py-2 text-sm font-semibold text-[#07472B] hover:bg-[#E9E7DA] disabled:opacity-50";
const dangerClass = "rounded-sm border border-[#9B3E35]/40 px-4 py-2 text-sm font-semibold text-[#9B3E35] hover:bg-[#F0E3DA] disabled:opacity-50";

function messageOf(error: unknown) {
  if (typeof error === "object" && error && "message" in error && typeof error.message === "string") return error.message;
  return "Something went wrong. Please try again.";
}
function safeUrl(value: string | null) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}
function Website({ value }: { value: string | null }) {
  const url = safeUrl(value);
  return url ? <a href={url} target="_blank" rel="noopener noreferrer" className="break-all text-sm font-semibold text-[#07472B] underline underline-offset-4">Open submitted website ↗</a> : <p className="text-sm text-[#626C57]">No usable website supplied.</p>;
}
function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="block text-sm font-semibold">{label}{children}</label>;
}
function slugify(value: string) {
  return value.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 150).replace(/-$/, "");
}

function SuggestionEditor({ row, disabled, onAction }: { row: Suggestion; disabled: boolean; onAction: (action: Action) => void }) {
  const [listing, setListing] = useState<Listing>({ name: row.name, slug: slugify(row.name), city: row.city, state: row.state, description: "", website: row.website_url, organizer: row.organizer ?? "" });
  const [query, setQuery] = useState(row.name);
  const [matches, setMatches] = useState<Market[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [linkedId, setLinkedId] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setMatches([]); setLinkedId(""); setSearchError("");
    if (query.trim().length < 2) { setSearching(false); return; }
    setSearching(true);
    const timer = setTimeout(async () => {
      try {
        // Wildcards are removed so the search remains a literal name fragment.
        const fragment = query.trim().replace(/[%_\\]/g, "");
        if (fragment.length < 2) return;
        const { data, error } = await createClient().from("markets").select("id,name,city,state,slug").ilike("name", `%${fragment}%`).order("name").limit(20);
        if (error) throw error;
        if (active) setMatches(data ?? []);
      } catch (error) { if (active) setSearchError(messageOf(error)); }
      finally { if (active) setSearching(false); }
    }, 300);
    return () => { active = false; clearTimeout(timer); };
  }, [query]);
  function update(key: keyof Listing, value: string) { setListing(current => ({ ...current, [key]: value })); }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const clean = { ...listing, name: listing.name.trim(), city: listing.city.trim(), state: listing.state.trim().toUpperCase(), description: listing.description.trim(), slug: listing.slug.trim(), website: listing.website.trim(), organizer: cleanOrganizer(listing.organizer) };
    if (!clean.name || !clean.city || !clean.description || !/^[A-Z]{2}$/.test(clean.state) || !/^[a-z0-9]+(-[a-z0-9]+)*$/.test(clean.slug) || !safeUrl(clean.website)) {
      setError("Complete every listing field. Use a lowercase URL slug with hyphens, a two-letter state, and a full http:// or https:// website."); return;
    }
    onAction({ type: "publish", row, listing: clean });
  }
  return <div className="mt-6 border-t border-[#252521]/15 pt-6">
    <h3 className="font-serif text-2xl font-bold">Prepare the public listing</h3>
    <p className="mt-2 text-sm leading-relaxed text-[#55554E]">Check the source and existing directory first. Write a neutral description with verified facts. Submitted notes stay private.</p>
    <form onSubmit={submit} className="mt-5">
      <fieldset disabled={disabled} className="grid min-w-0 gap-4 md:grid-cols-2">
        <Field label="Market name"><input className={inputClass} value={listing.name} onChange={e => update("name", e.target.value)} maxLength={150} required /></Field>
        <Field label="URL slug"><input className={inputClass} value={listing.slug} onChange={e => update("slug", e.target.value)} maxLength={150} required /><span className="mt-1 block text-xs font-normal text-[#626C57]">Example: raleigh-makers-market</span></Field>
        <Field label="City"><input className={inputClass} value={listing.city} onChange={e => update("city", e.target.value)} maxLength={100} required /></Field>
        <Field label="State"><input className={inputClass} value={listing.state} onChange={e => update("state", e.target.value.toUpperCase())} maxLength={2} required /></Field>
        <div className="md:col-span-2"><Field label="Official website / event link"><input type="url" className={inputClass} value={listing.website} onChange={e => update("website", e.target.value)} maxLength={1000} required /></Field></div>
        <div className="md:col-span-2"><OrganizerField id={`publish-organizer-${row.id}`} value={listing.organizer} onChange={value => update("organizer", value)} disabled={disabled} /></div>
        <div className="md:col-span-2"><Field label="Public description"><textarea className={inputClass} rows={4} value={listing.description} onChange={e => update("description", e.target.value)} maxLength={2000} required placeholder="Where it takes place and what kind of market it is. Avoid unverified fees, schedules, or promotional claims." /></Field></div>
        <div className="md:col-span-2"><button type="submit" className="heritage-button disabled:opacity-50">Review & publish →</button></div>
      </fieldset>
    </form>
    {error && <p className="mt-3 text-sm text-[#9B3E35]" role="alert">{error}</p>}
    <div className="mt-7 border-t border-[#252521]/15 pt-5">
      <h4 className="font-semibold">Already listed?</h4>
      <p className="mt-1 text-sm text-[#55554E]">Link this suggestion to the existing market instead of creating another profile.</p>
      <Field label="Search existing market names"><input className={inputClass} value={query} disabled={disabled} onChange={e => setQuery(e.target.value)} placeholder="Type at least two characters" /></Field>
      {searching ? <p role="status" className="mt-2 text-sm text-[#626C57]">Searching directory…</p> : matches.length ? <label className="mt-3 block text-sm font-semibold">Matching market<select className={inputClass} value={linkedId} disabled={disabled} onChange={e => setLinkedId(e.target.value)}><option value="">Choose the matching market</option>{matches.map(m => <option key={m.id} value={m.id}>{m.name} — {m.city}, {m.state}</option>)}</select></label> : <p className="mt-2 text-sm text-[#626C57]">{query.trim().length < 2 ? "Enter a longer market name to search." : "No matches. Try a shorter part of the market name."}</p>}
      {searchError && <p role="alert" className="mt-2 text-sm text-[#9B3E35]">{searchError}</p>}
      <button type="button" className={`${secondaryClass} mt-3`} disabled={disabled || !linkedId || searching} onClick={() => onAction({ type: "decide", kind: "suggestions", row, status: "duplicate", linkedId })}>Mark as duplicate</button>
    </div>
  </div>;
}

export default function AdminPage() {
  const [userId, setUserId] = useState<string | null>(null);
  const identity = useRef<string | null>(null);
  const [checking, setChecking] = useState(true);
  const [allowedOwner, setAllowedOwner] = useState<string | null>(null);
  const [accessError, setAccessError] = useState("");
  const [accessChecking, setAccessChecking] = useState(false);
  const [kind, setKind] = useState<Kind>("suggestions");
  const [status, setStatus] = useState<Status>("pending");
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [queue, setQueue] = useState<Queue | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [editor, setEditor] = useState<string | null>(null);
  const [action, setAction] = useState<Action | null>(null);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const allowed = Boolean(userId && userId === allowedOwner);

  useEffect(() => {
    let active = true;
    let authChanged = false;
    const supabase = createClient();
    function accept(id: string | null) {
      if (!active) return;
      if (identity.current !== id) {
        identity.current = id;
        setAllowedOwner(null); setQueue(null); setAction(null); setEditor(null);
        setSuccess(""); setError(""); setAccessError("");
        setUserId(id); setAccessChecking(Boolean(id));
      }
      setChecking(false);
    }
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      authChanged = true; accept(session?.user.id ?? null);
    });
    void supabase.auth.getUser().then(({ data, error }) => {
      if (active && !authChanged) {
        accept(data.user?.id ?? null);
        if (error && error.name !== "AuthSessionMissingError") setAccessError(messageOf(error));
      }
    }).catch(error => { if (active && !authChanged) { accept(null); setAccessError(messageOf(error)); } });
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
        if (active && identity.current === userId) { setAllowedOwner(null); setAccessError(messageOf(error)); }
      } finally { if (active && identity.current === userId) setAccessChecking(false); }
    })();
    return () => { active = false; };
  }, [userId, refresh]);

  useEffect(() => {
    if (!allowed || !userId) return;
    let active = true;
    setLoading(true); setError(""); setQueue(null);
    void (async () => {
      try {
        const { data, error } = await createClient().rpc("btb_admin_queue_with_attendance", { p_kind: kind, p_status: status, p_offset: offset });
        if (error) throw error;
        if (active && identity.current === userId) {
          const result = data as Queue;
          if (offset > 0 && result.items.length === 0) setOffset(Math.max(0, offset - 20));
          else setQueue(result);
        }
      } catch (error) { if (active && identity.current === userId) setError(messageOf(error)); }
      finally { if (active && identity.current === userId) setLoading(false); }
    })();
    return () => { active = false; };
  }, [allowed, userId, kind, status, offset, refresh]);

  function resetView() { setAction(null); setEditor(null); setError(""); setSuccess(""); setQueue(null); setOffset(0); }
  async function confirm() {
    if (!action || !allowed || !userId || lock.current) return;
    const actor = userId;
    const submitted = action;
    lock.current = true; setBusy(true); setError(""); setSuccess("");
    try {
      const supabase = createClient();
      // Check again before dispatch in case another tab changed the session.
      const { data: authData, error: authError } = await supabase.auth.getUser();
      if (authError) throw authError;
      if (authData.user?.id !== actor || identity.current !== actor) throw new Error("Your signed-in account changed. Refresh before moderating.");
      if (submitted.type === "publish") {
        const l = submitted.listing;
        const { error } = await supabase.rpc("btb_admin_publish_market_with_organizer", { p_suggestion_id: submitted.row.id, p_name: l.name, p_slug: l.slug, p_city: l.city, p_state: l.state, p_description: l.description, p_website_url: l.website, p_organizer: l.organizer || null });
        if (error) throw error;
      } else {
        const { error } = await supabase.rpc("btb_admin_decide", { p_kind: submitted.kind, p_id: submitted.row.id, p_expected_status: submitted.row.status, p_status: submitted.status, p_linked_market_id: submitted.linkedId ?? null });
        if (error) throw error;
      }
      if (identity.current !== actor) return;
      setSuccess(submitted.type === "publish" ? "Market published. The suggestion is approved and linked to its listing." : `Decision saved: ${submitted.status}.`);
      setAction(null); setEditor(null); setRefresh(n => n + 1);
    } catch (error) { if (identity.current === actor) setError(messageOf(error)); }
    finally { lock.current = false; setBusy(false); }
  }
  function decide(row: Row, next: Status) { setError(""); setSuccess(""); setAction({ type: "decide", kind, row, status: next }); }
  function actions(row: Row) {
    return <div className="mt-5 flex flex-wrap gap-3">
      {kind !== "suggestions" && row.status !== "approved" && <button type="button" className={secondaryClass} disabled={busy || Boolean(action)} onClick={() => decide(row, "approved")}>Approve</button>}
      {row.status !== "rejected" && <button type="button" className={dangerClass} disabled={busy || Boolean(action)} onClick={() => decide(row, "rejected")}>Reject</button>}
      {kind !== "suggestions" && row.status !== "pending" && <button type="button" className={secondaryClass} disabled={busy || Boolean(action)} onClick={() => decide(row, "pending")}>Return to pending</button>}
    </div>;
  }
  return <main className="mx-auto min-h-[65vh] max-w-6xl px-6 py-12 md:py-16">
    <p className="heritage-label">Behind the scenes</p>
    <h1 className="heritage-heading mt-4 text-4xl md:text-5xl">Community moderation.</h1>
    <p className="mt-4 max-w-3xl leading-relaxed text-[#55554E]">Review submissions, verify vendors, and keep the directory useful. This area is restricted to your admin account.</p>
    {checking || (userId && accessChecking && !allowed) ? <p className="mt-10" role="status">Checking admin access…</p> : !userId ? <div className="heritage-card mt-8"><h2 className="font-serif text-2xl font-bold">Sign in to continue.</h2><p className="mt-3 text-[#55554E]">Use the account configured as your administrator, then return here.</p><Link href="/login" className="heritage-button mt-5">Sign in →</Link></div> : !allowed ? <div className="heritage-card mt-8"><h2 className="font-serif text-2xl font-bold">{accessError ? "Unable to check access" : "Admin access required"}</h2><p className="mt-3 break-words text-[#55554E]">{accessError || "This account does not have permission to moderate submissions."}</p><div className="mt-5 flex flex-wrap gap-3"><Link href="/login" className={secondaryClass}>My Account / switch account</Link><button type="button" className={secondaryClass} onClick={() => setRefresh(n => n + 1)}>Try again</button></div></div> : <>
      <div className="mt-8 flex flex-wrap items-center gap-3 border-b border-[#252521]/20 pb-5" aria-label="Moderation queues">
        {(Object.keys(labels) as Kind[]).map(key => <button key={key} type="button" aria-pressed={kind === key} disabled={busy || Boolean(action)} onClick={() => { resetView(); setKind(key); setStatus("pending"); }} className={`rounded-sm border px-4 py-3 text-sm font-semibold disabled:opacity-50 ${kind === key ? "border-[#07472B] bg-[#07472B] text-white" : "border-[#252521]/20 hover:bg-[#E9E7DA]"}`}>{labels[key]}{queue && <span className="ml-2 rounded-full bg-white/20 px-2 py-0.5">{queue.pending[key]}</span>}</button>)}
      </div>
      <div className="my-6 flex flex-wrap items-end justify-between gap-4">
        <label className="text-sm font-semibold">Show status<select className={inputClass} value={status} disabled={busy || Boolean(action)} onChange={e => { resetView(); setStatus(e.target.value as Status); }}><option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option>{kind === "suggestions" && <option value="duplicate">Duplicate</option>}</select></label>
        <button type="button" className={secondaryClass} disabled={busy || loading || Boolean(action)} onClick={() => { setEditor(null); setRefresh(n => n + 1); }}>Refresh queues</button>
      </div>
      {success && <div role="status" className="mb-5 border-l-2 border-[#07472B] bg-[#E9E7DA] p-4 text-sm">{success}</div>}
      {error && <div role="alert" className="mb-5 break-words border-l-2 border-[#9B3E35] bg-[#F0E3DA] p-4 text-sm text-[#9B3E35]">{error} {success ? "The decision was saved, but the queue could not refresh." : "Refresh the queue before retrying if the connection was interrupted."}</div>}
      {action && <section aria-label="Confirm moderation decision" className="mb-6 border-2 border-[#07472B] bg-[#E9E7DA] p-5 md:p-6">
        <h2 className="font-serif text-2xl font-bold">{action.type === "publish" ? "Publish this market?" : `Change status to ${action.status}?`}</h2>
        {action.type === "publish" ? <div className="mt-3 space-y-2 text-sm"><p className="font-semibold">{action.listing.name} — {action.listing.city}, {action.listing.state}</p><p className="break-all">/markets/{action.listing.slug}</p><p className="whitespace-pre-wrap">{action.listing.description}</p><p className="break-all">{action.listing.website}</p><p>Organizer: {action.listing.organizer || "Not assigned"}</p><p>The listing will become public and its suggestion will be approved.</p></div> : <p className="mt-3 text-sm">{"business_name" in action.row ? action.row.business_name : "name" in action.row ? action.row.name : `Review of ${action.row.market_name}`} — {action.row.status} → {action.status}. {action.kind === "reviews" ? "Only approved reviews appear in member reports and rating averages." : action.kind === "vendors" ? "Approved vendors can submit reviews. Existing review statuses are managed separately." : action.status === "duplicate" ? "This suggestion will link to the market you selected." : "This suggestion will not create a public listing."}</p>}
        <div className="mt-5 flex flex-wrap gap-3"><button type="button" className="heritage-button disabled:opacity-50" disabled={busy} onClick={() => void confirm()}>{busy ? "Saving…" : action.type === "publish" ? "Confirm publication" : "Confirm decision"}</button><button type="button" className={secondaryClass} disabled={busy} onClick={() => setAction(null)}>Cancel</button></div>
      </section>}
      {loading ? <p role="status" className="py-8">Loading {labels[kind].toLowerCase()}…</p> : queue && !queue.items.length ? <div className="heritage-card py-10 text-center"><h2 className="font-serif text-2xl font-bold">No {status} {labels[kind].toLowerCase()}.</h2><p className="mt-3 text-sm text-[#626C57]">You&apos;re up to date for this queue.</p></div> : <div className="space-y-5">{queue?.items.map(row => <article key={row.id} className="rounded-sm border border-[#252521]/20 bg-[#FFFCF6] p-5 md:p-7">
        <div className="flex flex-wrap items-center justify-between gap-3"><p className="heritage-label">{row.status}</p><p className="text-xs text-[#626C57]">Submitted {new Date(row.created_at).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" })}</p></div>
        {"name" in row ? <>
          <h2 className="mt-3 font-serif text-2xl font-bold">{row.name}</h2><p className="mt-1 text-sm text-[#626C57]">{row.city}, {row.state}</p><div className="mt-4"><Website value={row.website_url} /></div>
          {row.organizer && <p className="mt-3 text-sm text-[#55554E]"><strong>Submitted organizer (unverified):</strong> {row.organizer}</p>}
          {row.notes && <div className="mt-4 bg-[#F4F0E6] p-4"><p className="text-xs font-bold uppercase tracking-wider text-[#626C57]">Private submission notes</p><p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed">{row.notes}</p></div>}
          {row.linked_slug && <Link href={`/markets/${row.linked_slug}`} className="mt-4 inline-block text-sm font-semibold text-[#07472B] underline">View linked market →</Link>}
          {row.status === "pending" && <><div className="mt-5 flex flex-wrap gap-3"><button type="button" className={secondaryClass} disabled={busy || Boolean(action)} onClick={() => setEditor(editor === row.id ? null : row.id)}>{editor === row.id ? "Close listing editor" : "Prepare listing / check duplicate"}</button><button type="button" className={dangerClass} disabled={busy || Boolean(action)} onClick={() => decide(row, "rejected")}>Reject suggestion</button></div>{editor === row.id && <SuggestionEditor key={row.id} row={row} disabled={busy || Boolean(action)} onAction={next => { setError(""); setSuccess(""); setAction(next); }} />}</>}
        </> : "business_name" in row ? <>
          <h2 className="mt-3 font-serif text-2xl font-bold">{row.business_name}</h2><div className="mt-4"><Website value={row.business_url} /></div><p className="mt-4 text-xs font-bold uppercase tracking-wider text-[#626C57]">Private verification details</p><p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed">{row.verification_notes}</p>{actions(row)}
        </> : <>
          <h2 className="mt-3 font-serif text-2xl font-bold">Review of {row.market_name}</h2><Link href={`/markets/${row.market_slug}`} className="mt-2 inline-block text-sm font-semibold text-[#07472B] underline">View market →</Link>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">{([ ["Overall", row.overall], ["Booth value", row.booth_value], ["Foot traffic", row.foot_traffic], ["Organization", row.organization], ["Promotion", row.promotion] ] as [string, number][]).map(([label, score]) => <div key={label} className="bg-[#F4F0E6] px-3 py-2"><p className="text-xs text-[#626C57]">{label}</p><p className="mt-1 text-lg font-bold" style={{ color: getRatingColor(score) }}>{score.toFixed(1)} / 5</p></div>)}</div>
          <p className="mt-4 text-sm"><strong>Vendor categories:</strong> {row.vendor_categories.join(", ") || "Not supplied"}{row.other_category ? ` — ${row.other_category}` : ""}</p>
          <p className="mt-3 text-sm font-semibold">{row.attended_on ? `Attended: ${formatAttendanceDate(row.attended_on)}` : "Attendance date not provided"}</p>
          <p className="mt-3 whitespace-pre-wrap break-words leading-relaxed">{row.experience}</p>
          <p className="mt-4 text-sm"><strong>Reported booth cost:</strong> {row.booth_cost === null ? "Not supplied" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(row.booth_cost)} · {row.booth_duration === "single" ? "Single day" : row.booth_duration === "multi" ? `Multiple days${row.number_of_days ? ` (${row.number_of_days})` : ""}` : "Duration not supplied"}</p><p className="mt-2 text-sm"><strong>Would return:</strong> {row.would_return}</p>{actions(row)}
        </>}
      </article>)}</div>}
      {queue && queue.total > 0 && <div className="mt-6 flex flex-wrap items-center justify-between gap-4 text-sm"><span>{offset + 1}–{Math.min(offset + 20, queue.total)} of {queue.total}</span><div className="flex gap-3"><button type="button" className={secondaryClass} disabled={!offset || busy || Boolean(action)} onClick={() => { setEditor(null); setOffset(n => Math.max(0, n - 20)); }}>Previous</button><button type="button" className={secondaryClass} disabled={offset + 20 >= queue.total || busy || Boolean(action)} onClick={() => { setEditor(null); setOffset(n => n + 20); }}>Next</button></div></div>}
    </>}
    {accessError && !userId && <p role="alert" className="mt-4 text-sm text-[#9B3E35]">{accessError}</p>}
  </main>;
}
