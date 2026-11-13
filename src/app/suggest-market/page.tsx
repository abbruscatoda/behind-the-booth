"use client";

import Link from "next/link";
import OrganizerField from "../../components/OrganizerField";
import { cleanOrganizer } from "../../lib/marketOrganizers";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { createClient } from "../../lib/supabase/client";

type Suggestion = {
  id: string;
  name: string;
  organizer: string | null;
  city: string;
  state: string;
  status: "pending" | "approved" | "rejected" | "duplicate";
  created_at: string;
};

const suggestionFields = "id, name, city, state, status, created_at, organizer";
const inputClass = "mt-2 w-full border border-[#252521]/25 bg-[#FFFCF6] px-4 py-3 text-sm outline-none focus:border-[#07472B] disabled:opacity-60";
const statusDetails = {
  pending: { label: "Pending review", note: "Your suggestion is waiting for review before being added to the directory." },
  approved: { label: "Approved", note: "Your suggestion has been approved. Find the listing in the market directory." },
  rejected: { label: "Not approved", note: "This suggestion was reviewed and was not approved for the directory." },
  duplicate: { label: "Already listed", note: "This suggestion matches a market already in the directory." },
};

export default function SuggestMarketPage() {
  const [userId, setUserId] = useState<string | null>(null);
  const identity = useRef<string | null>(null);
  const [checking, setChecking] = useState(true);
  const [name, setName] = useState("");
  const [organizer, setOrganizer] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("NC");
  const [website, setWebsite] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [listOwner, setListOwner] = useState<string | null>(null);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let active = true;
    let authChanged = false;
    const supabase = createClient();
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      authChanged = true;
      if (!active) return;
      identity.current = session?.user.id ?? null;
      setUserId(identity.current);
      setChecking(false);
      if (event === "SIGNED_OUT") {
        setSuggestions([]);
        setMessage("");
        setError("");
        setName("");
        setOrganizer("");
        setCity("");
        setWebsite("");
        setNotes("");
      }
    });
    async function checkUser() {
      try {
        const { data, error } = await supabase.auth.getUser();
        if (active && !authChanged) {
          identity.current = !error && data.user ? data.user.id : null;
          setUserId(identity.current);
        }
      } catch {
        if (active && !authChanged) {
          identity.current = null;
          setUserId(null);
        }
      } finally {
        if (active) setChecking(false);
      }
    }
    void checkUser();
    return () => { active = false; subscription.unsubscribe(); };
  }, []);

  useEffect(() => {
    let active = true;
    setSuggestions([]);
    setListOwner(null);
    setListError("");
    if (!userId) {
      setListLoading(false);
      return () => { active = false; };
    }
    const currentUser = userId;
    setListLoading(true);
    async function loadSuggestions() {
      try {
        const supabase = createClient();
        const { data, error } = await supabase.from("market_suggestions")
          .select(suggestionFields)
          .eq("submitted_by", currentUser)
          .order("created_at", { ascending: false })
          .limit(10);
        if (error) throw error;
        if (active) {
          setSuggestions((data ?? []) as Suggestion[]);
          setListOwner(currentUser);
        }
      } catch (cause) {
        console.error("Unable to load market suggestions:", cause);
        if (active) setListError("We couldn't load your recent suggestions. Please try again.");
      } finally {
        if (active) setListLoading(false);
      }
    }
    void loadSuggestions();
    return () => { active = false; };
  }, [userId, refresh]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    setError("");
    setMessage("");

    const marketName = name.trim();
    const marketOrganizer = cleanOrganizer(organizer);
    if (marketOrganizer.length > 120 || /[\u0000-\u001f\u007f]/.test(marketOrganizer)) {
      setError("Use an organizer name of at most 120 characters, without control characters.");
      return;
    }
    const marketCity = city.trim();
    const marketState = state.trim().toUpperCase();
    const sourceUrl = website.trim();
    if (!marketName || !marketCity) {
      setError("Please enter the market name and city.");
      return;
    }
    if (!/^[A-Z]{2}$/.test(marketState)) {
      setError("Use a two-letter state abbreviation, such as NC.");
      return;
    }
    try {
      const parsed = new URL(sourceUrl);
      if (!/^https?:$/.test(parsed.protocol) || /\s/.test(sourceUrl) || parsed.username || parsed.password) {
        throw new Error("Invalid URL");
      }
    } catch {
      setError("Enter a complete public website or event link starting with https:// or http://.");
      return;
    }

    submitting.current = true;
    setBusy(true);
    const submittingUser = userId;
    try {
      const supabase = createClient();
      const { data: auth, error: authError } = await supabase.auth.getUser();
      if (authError || !auth.user) throw new Error("Please sign in again before submitting.");
      if (auth.user.id !== submittingUser) throw new Error("Your signed-in account changed. Refresh this page before submitting.");
      const { error: insertError } = await supabase.from("market_suggestions").insert({
        submitted_by: auth.user.id,
        name: marketName,
        city: marketCity,
        state: marketState,
        website_url: sourceUrl,
        notes: notes.trim() || null,
        organizer: marketOrganizer || null,
      });
      if (insertError) {
        if (insertError.code === "42501") throw new Error("You don't have permission to submit this suggestion. Please sign in and try again.");
        throw insertError;
      }
      if (identity.current === submittingUser) {
        setMessage(`Thanks! Your suggestion for ${marketName} was submitted for review. It will appear in the directory only after approval.`);
        setName("");
        setOrganizer("");
        setCity("");
        setState("NC");
        setWebsite("");
        setNotes("");
        setRefresh((previous) => previous + 1);
      }
    } catch (cause) {
      console.error("Unable to submit market suggestion:", cause);
      if (identity.current === submittingUser) {
        setError(cause instanceof Error ? cause.message : "We couldn't submit your suggestion. Please try again.");
      }
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  const ownSuggestions = listOwner === userId ? suggestions : [];

  return (
    <main className="flex-1 bg-[#F4F0E6] text-[#252521]">
      <section className="mx-auto max-w-3xl px-6 py-12 md:py-16">
        <Link href="/markets" className="text-sm font-semibold text-[#07472B] hover:underline">← Back to Market Directory</Link>
        <p className="heritage-label mt-10">Built by the Vendor Community</p>
        <h1 className="heritage-heading mt-4 text-4xl md:text-5xl">Know a market we should know?</h1>
        <p className="mt-5 max-w-2xl leading-relaxed text-[#55554E]">Help us discover markets, festivals, and pop-ups around Raleigh and the Triangle. Share a public source so we can check the details before adding a listing.</p>
        <div className="mt-6 border-l-2 border-[#07472B] bg-[#E9E7DA] px-5 py-4 text-sm leading-relaxed text-[#55554E]">Please <Link href="/markets" className="font-semibold text-[#07472B] underline underline-offset-2">search the directory</Link> first. Recurring dates usually belong to the same market profile. Suggesting a market does not submit a review or give it a rating.</div>

        {checking ? <p className="mt-8" role="status">Checking your sign-in...</p> : !userId ? (
          <div className="heritage-card mt-8">
            <h2 className="font-serif text-2xl font-bold">Sign in to suggest a market.</h2>
            <p className="mt-3 text-sm leading-relaxed text-[#55554E]">Any signed-in member can make a suggestion. Vendor verification is required only to write reviews.</p>
            <Link href="/login" className="heritage-button mt-5">Sign In / Create Free Account →</Link>
          </div>
        ) : (
          <>
            <form onSubmit={handleSubmit} className="heritage-card mt-8">
              <fieldset disabled={busy} className="min-w-0 space-y-6">
                <legend className="sr-only">Suggest a market</legend>
                <div>
                  <label htmlFor="market-name" className="text-sm font-semibold">Market or Event Name <span className="font-normal text-[#626C57]">(required)</span></label>
                  <input id="market-name" type="text" required maxLength={150} value={name} onChange={(event) => setName(event.target.value)} placeholder="Use the name shown by the organizer" className={inputClass} />
                </div>
                <OrganizerField id="suggestion-organizer" value={organizer} onChange={setOrganizer} disabled={busy} hint="If you know who runs this market, choose an existing name or type a new one. Leave blank if you’re unsure. We’ll verify it before adding a public organizer tag." />
                <div className="grid gap-5 sm:grid-cols-[minmax(0,1fr)_120px]">
                  <div><label htmlFor="market-city" className="text-sm font-semibold">City <span className="font-normal text-[#626C57]">(required)</span></label><input id="market-city" type="text" required maxLength={100} value={city} onChange={(event) => setCity(event.target.value)} placeholder="e.g., Raleigh" className={inputClass} /></div>
                  <div><label htmlFor="market-state" className="text-sm font-semibold">State</label><input id="market-state" type="text" required minLength={2} maxLength={2} pattern="[A-Za-z]{2}" value={state} onChange={(event) => setState(event.target.value.toUpperCase())} className={inputClass} /></div>
                </div>
                <div>
                  <label htmlFor="market-website" className="text-sm font-semibold">Official Website or Event Link <span className="font-normal text-[#626C57]">(required)</span></label>
                  <p id="website-help" className="mt-2 text-xs leading-relaxed text-[#626C57]">Use the organizer’s website, official event page, or public business social post. This helps us confirm that the market exists.</p>
                  <input id="market-website" type="url" required maxLength={1000} value={website} onChange={(event) => setWebsite(event.target.value)} placeholder="https://..." aria-describedby="website-help" className={inputClass} />
                </div>
                <div>
                  <label htmlFor="market-notes" className="text-sm font-semibold">Anything Else We Should Know? <span className="font-normal text-[#626C57]">(optional)</span></label>
                  <p id="notes-help" className="mt-2 text-xs leading-relaxed text-[#626C57]">Include known dates, the venue, or why it is relevant to vendors. Leave unknown details out. Please do not include private contact information.</p>
                  <textarea id="market-notes" rows={4} maxLength={2000} value={notes} onChange={(event) => setNotes(event.target.value)} aria-describedby="notes-help" className={inputClass} />
                  <p className="mt-1 text-right text-xs text-[#626C57]">{notes.length} / 2000 characters</p>
                </div>
                <div className="flex flex-wrap items-center gap-4 border-t border-[#252521]/15 pt-5">
                  <button type="submit" className="heritage-button disabled:cursor-wait disabled:opacity-50">{busy ? "Submitting..." : "Suggest This Market"}</button>
                  <p className="text-xs text-[#626C57]">Suggestions are reviewed before publication.</p>
                </div>
              </fieldset>
            </form>

            {message && <p role="status" className="mt-5 border-l-2 border-[#07472B] bg-[#E9E7DA] p-5 text-sm leading-relaxed">{message}</p>}
            {error && <p role="alert" className="mt-5 border-l-2 border-[#9B3E35] bg-[#E9E7DA] p-5 text-sm leading-relaxed text-[#9B3E35]">{error}</p>}

            <section className="mt-12 border-t border-[#252521]/20 pt-7">
              <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-serif text-2xl font-bold">Your Recent Suggestions</h2><button type="button" onClick={() => setRefresh((previous) => previous + 1)} disabled={listLoading || busy} className="text-xs font-semibold text-[#07472B] underline underline-offset-4 disabled:opacity-50">Refresh Status</button></div>
              <p className="mt-2 text-xs text-[#626C57]">Your 10 most recent suggestions. This list is visible only to your account.</p>
              {listLoading ? <p role="status" className="mt-5 text-sm text-[#55554E]">Loading suggestions...</p> : listError ? <p role="alert" className="mt-5 text-sm text-[#9B3E35]">{listError}</p> : ownSuggestions.length === 0 ? <p className="mt-5 text-sm text-[#55554E]">You haven’t suggested any markets yet.</p> : (
                <ul className="mt-5 space-y-3">{ownSuggestions.map((suggestion) => (
                  <li key={suggestion.id} className="border border-[#252521]/20 bg-[#FFFCF6] p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="font-serif text-xl font-bold">{suggestion.name}</h3><span className="border border-[#07472B]/25 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-[#07472B]">{statusDetails[suggestion.status].label}</span></div>
                    <p className="mt-2 text-xs text-[#626C57]">{suggestion.city}, {suggestion.state}</p>
                    {suggestion.organizer && <p className="mt-2 text-xs text-[#626C57]">Suggested organizer: {suggestion.organizer}</p>}
                    <p className="mt-3 text-sm leading-relaxed text-[#55554E]">{statusDetails[suggestion.status].note}</p>
                    {(suggestion.status === "approved" || suggestion.status === "duplicate") && <Link href="/markets" className="mt-3 inline-block text-xs font-semibold text-[#07472B] underline">Browse the Directory →</Link>}
                  </li>
                ))}</ul>
              )}
            </section>
          </>
        )}
      </section>
    </main>
  );
}
