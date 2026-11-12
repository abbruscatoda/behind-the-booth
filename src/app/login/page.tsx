"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { createClient } from "../../lib/supabase/client";

type Mode = "signin" | "signup";
type VendorProfile = {
  business_name: string;
  verification_status: "pending" | "approved" | "rejected";
};

export default function LoginPage() {
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [userId, setUserId] = useState<string | null>(null);
  const [checking, setChecking] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [profile, setProfile] = useState<VendorProfile | null>(null);
  const [profileOwner, setProfileOwner] = useState<string | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [profileRefresh, setProfileRefresh] = useState(0);
  const submitting = useRef(false);
  const signedIn = userId !== null;

  useEffect(() => {
    const supabase = createClient();
    let active = true;
    let authChanged = false;
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      authChanged = true;
      if (active) {
        setUserId(session?.user.id ?? null);
        setChecking(false);
      }
    });
    async function checkUser() {
      try {
        const { data, error } = await supabase.auth.getUser();
        if (active && !authChanged) setUserId(!error && data.user ? data.user.id : null);
      } catch {
        if (active && !authChanged) setUserId(null);
      } finally {
        if (active) setChecking(false);
      }
    }
    void checkUser();
    return () => { active = false; subscription.unsubscribe(); };
  }, []);

  useEffect(() => {
    let active = true;
    setProfile(null);
    setProfileOwner(null);
    setProfileError("");
    if (!userId) {
      setProfileLoading(false);
      return () => { active = false; };
    }
    const currentUserId = userId;
    setProfileLoading(true);
    async function loadProfile() {
      try {
        const supabase = createClient();
        const { data, error } = await supabase.from("vendor_profiles")
          .select("business_name, verification_status")
          .eq("user_id", currentUserId).maybeSingle();
        if (error) throw error;
        if (active) {
          setProfile(data);
          setProfileOwner(currentUserId);
        }
      } catch (cause) {
        console.error("Unable to load vendor status:", cause);
        if (active) setProfileError("We couldn't load your vendor status. Your member access is still available.");
      } finally {
        if (active) setProfileLoading(false);
      }
    }
    void loadProfile();
    return () => { active = false; };
  }, [userId, profileRefresh]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const supabase = createClient();
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email: email.trim(), password,
          options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
        });
        if (error) throw error;
        setPassword("");
        if (data.session) {
          setUserId(data.session.user.id);
          setMessage("Your account is ready. You are signed in.");
        } else {
          setMessage("Check your email for a confirmation link. Open it in this same browser on this computer. Check your spam folder too. If you already have an account, use Sign In.");
        }
      } else {
        const { data, error } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
        if (error) throw error;
        setPassword("");
        setUserId(data.user.id);
        setMessage("You are signed in.");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Something went wrong. Please try again.");
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  async function handleSignOut() {
    if (submitting.current) return;
    submitting.current = true;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      setUserId(null);
      setProfile(null);
      setProfileOwner(null);
      setPassword("");
      setMessage("You have signed out.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to sign out. Please try again.");
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  }

  function changeMode(nextMode: Mode) {
    setMode(nextMode);
    setPassword("");
    setMessage("");
    setError("");
  }

  const currentProfile = profileOwner === userId ? profile : null;
  const statusReady = !profileLoading && profileOwner === userId;
  const status = currentProfile?.verification_status;
  const statusLabel = status === "approved" ? "Approved Vendor" : status === "pending" ? "Pending Review" : status === "rejected" ? "Not Approved" : "Not Yet Verified";
  const statusDescription = status === "approved"
    ? "Your vendor account is approved. You can submit firsthand market reviews for moderation."
    : status === "pending"
      ? "Your application has been received and is waiting for review. You can keep reading full market reports while you wait."
      : status === "rejected"
        ? "Your vendor application was not approved. You can still read full market reports. Application editing and resubmission are not available yet."
        : "Want to share your own experience? Apply for vendor verification before submitting reviews. You can already read full market reports.";

  return (
    <main className="flex-1 bg-[#F4F0E6] text-[#252521]">
      
      

      <section className="mx-auto max-w-2xl px-6 py-14 md:py-20">
        <p className="heritage-label">{signedIn ? "My Account" : "The Vendor Community"}</p>
        <h1 className="heritage-heading mt-5 text-4xl md:text-5xl">{signedIn ? "Welcome back." : mode === "signup" ? "Join the conversation." : "Take your place."}</h1>
        <p className="mt-6 leading-relaxed text-[#55554E]">Your free account unlocks full vendor reports and approved reviews. Reviews do not publicly display your account name or email. Vendor verification is required to submit reviews.</p>

        {checking ? <p className="mt-10 text-[#55554E]" role="status">Checking your sign-in...</p> : signedIn ? (
          <div className="mt-8 space-y-4">
            <section className="border border-[#252521]/20 bg-[#FFFCF6] p-5 sm:p-6">
              <p className="heritage-label">Free Membership</p>
              <h2 className="mt-3 font-serif text-2xl font-bold">Your full vendor report access is active.</h2>
              <p className="mt-3 text-sm leading-relaxed text-[#55554E]">Read approved reviews, explore all five rating breakdowns, compare reported booth costs within a market, and see whether vendors would return.</p>
              <Link href="/markets" className="heritage-button mt-5 inline-block">Explore Markets →</Link>
            </section>

            <section className="border border-[#252521]/20 p-5 sm:p-6" aria-labelledby="vendor-status-heading">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 id="vendor-status-heading" className="heritage-label">Vendor Verification</h2>
                {statusReady && !profileError && <span className={`border px-3 py-1 text-[11px] font-bold uppercase tracking-wider ${status === "approved" ? "border-[#626C57] text-[#07472B]" : "border-[#D6D4BF] text-[#07472B]"}`}>{statusLabel}</span>}
              </div>
              {profileError ? (
                <div className="mt-4">
                  <p role="alert" className="text-sm leading-relaxed text-[#07472B]">{profileError}</p>
                  <button type="button" onClick={() => setProfileRefresh((previous) => previous + 1)} className="mt-4 text-sm font-semibold text-[#07472B] underline">Retry Status Check</button>
                  <Link href="/verify" className="ml-5 inline-block text-sm font-semibold text-[#07472B] underline">Open Verification →</Link>
                </div>
              ) : !statusReady ? <p className="mt-4 text-sm text-[#55554E]" role="status">Checking your vendor status...</p> : (
                <>
                  <h3 className="mt-4 font-serif text-2xl font-bold">{currentProfile?.business_name ?? "Share your vendor experience."}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-[#55554E]">{statusDescription}</p>
                  <div className="mt-5 flex flex-wrap items-center gap-5">
                    <Link href="/verify" className="text-sm font-semibold text-[#07472B] underline underline-offset-4">{status === "approved" ? "View Verification" : status === "pending" ? "View Application Status" : status === "rejected" ? "View Application" : "Apply for Vendor Verification"} →</Link>
                    <button type="button" onClick={() => setProfileRefresh((previous) => previous + 1)} className="text-xs text-[#626C57] underline underline-offset-4">Refresh Status</button>
                  </div>
                </>
              )}
              <p className="mt-5 border-t border-[#252521]/15 pt-4 text-xs leading-relaxed text-[#626C57]">Business information submitted for verification stays private. Email confirmation verifies your email address; vendor approval is a separate review.</p>
            </section>
            <button type="button" onClick={handleSignOut} disabled={busy} className="mt-3 text-sm font-semibold text-[#07472B] underline underline-offset-4 disabled:opacity-50">{busy ? "Please wait..." : "Sign Out"}</button>
          </div>
        ) : (
          <div className="heritage-card mt-8">
            <div className="mb-8 flex gap-6 border-b border-[#252521]/20 pb-5">
              <button type="button" onClick={() => changeMode("signin")} disabled={busy} aria-pressed={mode === "signin"} className={`text-sm font-bold ${mode === "signin" ? "text-[#07472B] underline underline-offset-8" : "text-[#626C57]"}`}>Sign In</button>
              <button type="button" onClick={() => changeMode("signup")} disabled={busy} aria-pressed={mode === "signup"} className={`text-sm font-bold ${mode === "signup" ? "text-[#07472B] underline underline-offset-8" : "text-[#626C57]"}`}>Create Account</button>
            </div>
            <form onSubmit={handleSubmit}>
              <label htmlFor="email" className="block text-sm font-semibold">Email Address</label>
              <input id="email" type="email" autoComplete="email" required disabled={busy} value={email} onChange={(event) => setEmail(event.target.value)} className="mt-3 w-full border border-[#D6D4BF] bg-[#FFFCF6] px-4 py-3 outline-none focus:border-[#07472B]" />
              <label htmlFor="password" className="mt-6 block text-sm font-semibold">Password</label>
              <input id="password" type="password" autoComplete={mode === "signup" ? "new-password" : "current-password"} minLength={mode === "signup" ? 8 : undefined} required disabled={busy} value={password} onChange={(event) => setPassword(event.target.value)} className="mt-3 w-full border border-[#D6D4BF] bg-[#FFFCF6] px-4 py-3 outline-none focus:border-[#07472B]" />
              {mode === "signup" && <p className="mt-2 text-xs text-[#626C57]">Use at least 8 characters. Membership is free.</p>}
              {mode === "signin" && <Link href="/forgot-password" className="mt-4 inline-block text-sm font-semibold text-[#07472B] underline underline-offset-4">Forgot your password?</Link>}
              <button type="submit" disabled={busy} className="heritage-button mt-8 w-full disabled:cursor-wait disabled:opacity-50">{busy ? "Please wait..." : mode === "signup" ? "Create My Free Account" : "Sign In"}</button>
            </form>
          </div>
        )}

        {message && <div role="status" className="mt-6 border-l-2 border-[#626C57] bg-[#E9E7DA] p-5 text-sm leading-relaxed">{message}</div>}
        {error && <div role="alert" className="mt-6 border-l-2 border-[#07472B] bg-[#E9E7DA] p-5 text-sm leading-relaxed text-[#07472B]">{error}</div>}
      </section>
    </main>
  );
}
