"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { createClient } from "../../lib/supabase/client";

export default function ResetPasswordPage() {
  const [checking, setChecking] = useState(true);
  const [userId, setUserId] = useState<string | null>(null);
  const identity = useRef<string | null>(null);
  const [accountEmail, setAccountEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const submitting = useRef(false);
  const saved = useRef(false);
  const mounted = useRef(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");
  const [signOutFailed, setSignOutFailed] = useState(false);

  useEffect(() => {
    let active = true;
    let validated = false;
    let observedId: string | null | undefined;
    mounted.current = true;
    const supabase = createClient();
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      observedId = session?.user.id ?? null;
      if (active && validated && observedId !== identity.current) {
        identity.current = null; setUserId(null); setAccountEmail("");
        setPassword(""); setConfirmation("");
        if (!saved.current) setError("Your session changed or expired. Request a new reset link.");
      }
    });
    void (async () => {
      try {
        const { data, error } = await supabase.auth.getUser();
        if (!active) return;
        validated = true;
        if (error || !data.user || (observedId !== undefined && observedId !== data.user.id)) {
          identity.current = null; setUserId(null); return;
        }
        identity.current = data.user.id;
        setUserId(data.user.id); setAccountEmail(data.user.email ?? "");
      } catch {
        if (active) { identity.current = null; setUserId(null); }
      } finally { if (active) setChecking(false); }
    })();
    return () => { active = false; mounted.current = false; subscription.unsubscribe(); };
  }, []);

  async function finishSignOut() {
    const { error } = await createClient().auth.signOut({ scope: "global" });
    if (mounted.current) setSignOutFailed(Boolean(error));
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current || saved.current || !userId) return;
    setError("");
    if (password.length < 8) { setError("Use at least 8 characters for your new password."); return; }
    if (password !== confirmation) { setError("The passwords don't match. Please enter them again."); return; }
    const actor = userId;
    submitting.current = true; setBusy(true);
    try {
      const supabase = createClient();
      const { data: current, error: userError } = await supabase.auth.getUser();
      if (!mounted.current) return;
      if (userError || current.user?.id !== actor || identity.current !== actor) {
        identity.current = null; setUserId(null); setPassword(""); setConfirmation("");
        setError("Your session changed or expired. Request a new reset link."); return;
      }
      // Supabase authorizes this for the current user. No admin API or database write.
      const { error } = await supabase.auth.updateUser({ password });
      if (!mounted.current || identity.current !== actor) return;
      if (error) {
        if (error.status === 401 || error.status === 403) {
          identity.current = null; setUserId(null); setPassword(""); setConfirmation("");
          setError("Your session expired. Request a new reset link.");
        } else if (error.code === "same_password") setError("Choose a new password that is different from your current one.");
        else if (error.code === "weak_password") setError("Choose a stronger password. Your account's password rules may require more characters or a mix of letters, numbers, and symbols.");
        else setError("We couldn't confirm the password update. Try again, or request a fresh reset link if the problem continues.");
        return;
      }
      saved.current = true; setDone(true); setPassword(""); setConfirmation("");
      // Password success remains success even if the separate sign-out call fails.
      try { await finishSignOut(); }
      catch { if (mounted.current) setSignOutFailed(true); }
    } catch {
      if (mounted.current) setError("We couldn't confirm the password update. Check your connection. If it already succeeded, try signing in with the new password.");
    } finally {
      submitting.current = false;
      if (mounted.current) setBusy(false);
    }
  }
  async function retrySignOut() {
    if (submitting.current) return;
    submitting.current = true; setBusy(true);
    try { await finishSignOut(); }
    catch { if (mounted.current) setSignOutFailed(true); }
    finally { submitting.current = false; if (mounted.current) setBusy(false); }
  }

  return <main className="mx-auto min-h-[60vh] max-w-xl px-6 py-14 md:py-20">
    <p className="heritage-label">Account access</p>
    <h1 className="heritage-heading mt-5 text-4xl md:text-5xl">{done ? "You're back in control." : "Choose a new password."}</h1>
    {checking ? <p role="status" className="mt-8 text-[#55554E]">Checking your secure session…</p> : done ? <div className="heritage-card mt-8">
      <h2 className="font-serif text-2xl font-bold">Password updated.</h2>
      <p role="status" className="mt-4 leading-relaxed text-[#55554E]">Your new password has been saved. Your vendor status, reviews, and account information stay connected.</p>
      {busy ? <p role="status" className="mt-5 text-sm text-[#626C57]">Finishing sign-out…</p> : signOutFailed ? <div className="mt-5"><p role="alert" className="text-sm leading-relaxed text-[#9B3E35]">Your password was updated, but we couldn&apos;t finish signing you out. Try signing out again before testing the new password.</p><button type="button" onClick={() => void retrySignOut()} className="heritage-button mt-4">Try signing out again</button></div> : <Link href="/login" className="heritage-button mt-6">Sign in with your new password →</Link>}
    </div> : !userId ? <div className="heritage-card mt-8">
      <h2 className="font-serif text-2xl font-bold">Request a fresh reset link.</h2>
      <p className="mt-4 leading-relaxed text-[#55554E]">We couldn&apos;t verify an active session for this page. Request a password-reset email and open its newest link in the same browser on this device.</p>
      <Link href="/forgot-password" className="heritage-button mt-6">Request reset link →</Link>
    </div> : <div className="heritage-card mt-8">
      <p className="mb-6 break-words text-sm leading-relaxed text-[#55554E]">{accountEmail ? <>Updating the password for <strong>{accountEmail}</strong>.</> : "Update the password for your signed-in account."}</p>
      <form onSubmit={submit}>
        <label htmlFor="new-password" className="block text-sm font-semibold">New password</label>
        <input id="new-password" type={visible ? "text" : "password"} autoComplete="new-password" minLength={8} required disabled={busy} value={password} onChange={event => setPassword(event.target.value)} className="mt-3 w-full border border-[#D6D4BF] bg-[#FFFCF6] px-4 py-3 outline-none focus:border-[#07472B] disabled:opacity-60" />
        <p className="mt-2 text-xs leading-relaxed text-[#626C57]">Use at least 8 characters and a password you don&apos;t use elsewhere.</p>
        <label htmlFor="confirm-password" className="mt-6 block text-sm font-semibold">Confirm new password</label>
        <input id="confirm-password" type={visible ? "text" : "password"} autoComplete="new-password" minLength={8} required disabled={busy} value={confirmation} onChange={event => setConfirmation(event.target.value)} className="mt-3 w-full border border-[#D6D4BF] bg-[#FFFCF6] px-4 py-3 outline-none focus:border-[#07472B] disabled:opacity-60" />
        <label className="mt-4 flex items-center gap-2 text-sm text-[#55554E]"><input type="checkbox" checked={visible} disabled={busy} onChange={event => setVisible(event.target.checked)} className="accent-[#07472B]" />Show passwords</label>
        <button type="submit" disabled={busy} className="heritage-button mt-7 w-full disabled:opacity-50">{busy ? "Updating password…" : "Save new password →"}</button>
      </form>
    </div>}
    {error && !done && <div role="alert" className="mt-6 border-l-2 border-[#9B3E35] bg-[#F0E3DA] p-5 text-sm leading-relaxed text-[#9B3E35]">{error}</div>}
    {!done && <Link href="/forgot-password" className="mt-7 inline-block text-sm font-semibold text-[#07472B] underline underline-offset-4">Request another reset link</Link>}
  </main>;
}
