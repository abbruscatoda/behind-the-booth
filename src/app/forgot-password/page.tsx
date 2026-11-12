"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { createClient } from "../../lib/supabase/client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [invalidLink, setInvalidLink] = useState(false);
  const [error, setError] = useState("");
  const [retryAt, setRetryAt] = useState(0);
  const [remaining, setRemaining] = useState(0);
  const submitting = useRef(false);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    setInvalidLink(new URL(window.location.href).searchParams.get("recovery") === "invalid");
    return () => { mounted.current = false; };
  }, []);
  useEffect(() => {
    if (!retryAt) return;
    const tick = () => setRemaining(Math.max(0, Math.ceil((retryAt - Date.now()) / 1000)));
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [retryAt]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current || Date.now() < retryAt) return;
    const address = email.trim();
    if (!address || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address)) {
      setError("Enter a valid email address."); return;
    }
    submitting.current = true; setBusy(true); setError(""); setSent(false);
    try {
      const { error } = await createClient().auth.resetPasswordForEmail(address, {
        redirectTo: `${window.location.origin}/auth/recovery`,
      });
      if (!mounted.current) return;
      if (error) {
        if (error.status === 429 || error.code === "over_email_send_rate_limit" || error.code === "over_request_rate_limit") {
          setError("Too many email requests. Please wait before trying again.");
          setRetryAt(Date.now() + 60000); setRemaining(60);
        } else setError("We couldn't request a reset email right now. Please try again later.");
        return;
      }
      // Same result whether or not the email is registered.
      setSent(true); setInvalidLink(false);
      setRetryAt(Date.now() + 60000); setRemaining(60);
    } catch {
      if (mounted.current) setError("We couldn't request a reset email right now. Check your connection and try again.");
    } finally {
      submitting.current = false;
      if (mounted.current) setBusy(false);
    }
  }

  return <main className="mx-auto min-h-[60vh] max-w-xl px-6 py-14 md:py-20">
    <p className="heritage-label">Account access</p>
    <h1 className="heritage-heading mt-5 text-4xl md:text-5xl">Forgot your password?</h1>
    <p className="mt-5 leading-relaxed text-[#55554E]">Enter the email address you used for Behind the Booth. We&apos;ll help you get back to your account.</p>
    {invalidLink && <div role="alert" className="mt-6 border-l-2 border-[#AD573B] bg-[#E9E7DA] p-4 text-sm leading-relaxed">That reset link couldn&apos;t be verified. It may have expired, already been used, or been opened in a different browser. Request a fresh link below and open it in the browser where you make the request.</div>}
    <div className="heritage-card mt-8">
      <form onSubmit={submit}>
        <label htmlFor="recovery-email" className="block text-sm font-semibold">Email address</label>
        <input id="recovery-email" type="email" autoComplete="email" required maxLength={254} disabled={busy} value={email} onChange={event => setEmail(event.target.value)} className="mt-3 w-full border border-[#D6D4BF] bg-[#FFFCF6] px-4 py-3 outline-none focus:border-[#07472B] disabled:opacity-60" />
        <button type="submit" disabled={busy || remaining > 0} className="heritage-button mt-6 w-full disabled:cursor-not-allowed disabled:opacity-50">{busy ? "Requesting link…" : remaining > 0 ? `Try again in ${remaining}s` : sent ? "Request another link" : "Send reset link →"}</button>
      </form>
      <p className="mt-4 text-xs leading-relaxed text-[#626C57]">Open the email link in this same browser on this device. Check Spam too. If you request another link, use the newest email.</p>
    </div>
    {sent && <div role="status" className="mt-6 border-l-2 border-[#07472B] bg-[#E9E7DA] p-5 text-sm leading-relaxed"><strong>Check your inbox.</strong> If an account exists for that email address, you&apos;ll receive a password-reset link.</div>}
    {error && <div role="alert" className="mt-6 border-l-2 border-[#9B3E35] bg-[#F0E3DA] p-5 text-sm leading-relaxed text-[#9B3E35]">{error}</div>}
    <Link href="/login" className="mt-7 inline-block text-sm font-semibold text-[#07472B] underline underline-offset-4">← Back to sign in</Link>
  </main>;
}
