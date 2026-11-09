"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { createClient } from "../../lib/supabase/client";

type Mode = "signin" | "signup";

export default function LoginPage() {
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [signedIn, setSignedIn] = useState(false);
  const [checking, setChecking] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const supabase = createClient();
    let active = true;
    let authChanged = false;

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      authChanged = true;

      if (active) {
        setSignedIn(Boolean(session?.user));
        setChecking(false);
      }
    });

    async function checkUser() {
      try {
        const { data, error } = await supabase.auth.getUser();

        if (active && !authChanged) {
          setSignedIn(!error && Boolean(data.user));
        }
      } catch {
        if (active && !authChanged) {
          setSignedIn(false);
        }
      } finally {
        if (active) setChecking(false);
      }
    }

    void checkUser();

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");

    try {
      const supabase = createClient();

      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email: email.trim(),
          password,
          options: {
            emailRedirectTo: `${window.location.origin}/auth/callback`,
          },
        });

        if (error) throw error;

        setPassword("");

        if (data.session) {
          setSignedIn(true);
          setMessage("Your account is ready. You are signed in.");
        } else {
          setMessage(
            "Check your email for a confirmation link. Open it in this same browser on this computer. Check your spam folder too. If you already have an account, use Sign In."
          );
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });

        if (error) throw error;

        setPassword("");
        setSignedIn(true);
        setMessage("You are signed in.");
      }
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Something went wrong. Please try again."
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleSignOut() {
    setBusy(true);
    setError("");
    setMessage("");

    try {
      const supabase = createClient();
      const { error } = await supabase.auth.signOut();

      if (error) throw error;

      setSignedIn(false);
      setPassword("");
      setMessage("You have signed out.");
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Unable to sign out. Please try again."
      );
    } finally {
      setBusy(false);
    }
  }

  function changeMode(nextMode: Mode) {
    setMode(nextMode);
    setPassword("");
    setMessage("");
    setError("");
  }

  return (
    <main className="min-h-screen bg-[#F4F0E6] text-[#252521]">
      <div className="bg-[#252521] px-5 py-3 text-center text-xs font-semibold uppercase tracking-[0.2em] text-[#F4F0E6]">
        An independent resource for the vendor community
      </div>

      <header className="border-b border-[#252521]/20">
        <nav className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-5 px-6 py-7">
          <Link
            href="/"
            className="font-serif text-2xl font-black tracking-tight md:text-3xl"
          >
            Behind the Booth<span className="text-[#AD573B]">.</span>
          </Link>

          <Link
            href="/markets"
            className="text-sm font-semibold hover:text-[#AD573B]"
          >
            Explore Markets
          </Link>
        </nav>
      </header>

      <section className="mx-auto max-w-xl px-6 py-16 md:py-24">
        <p className="heritage-label">The Vendor Community</p>

        <h1 className="heritage-heading mt-5 text-4xl md:text-5xl">
          {signedIn
            ? "Welcome back."
            : mode === "signup"
              ? "Join the conversation."
              : "Take your place."}
        </h1>

        <p className="mt-6 leading-relaxed text-[#55554E]">
          Your account is private. Public reviews will appear without
          your account name or email. Email confirmation and vendor
          verification are separate steps.
        </p>

        {checking ? (
          <p className="mt-10 text-[#55554E]" role="status">
            Checking your sign-in...
          </p>
        ) : signedIn ? (
          <div className="heritage-card mt-10">
            <h2 className="font-serif text-2xl font-bold">
              You&apos;re signed in.
            </h2>

            <p className="mt-4 leading-relaxed text-[#55554E]">
              You can explore the market directory. Vendor verification
              and review submission are coming next.
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-5">
              <Link href="/markets" className="heritage-button">
                Explore Markets →
              </Link>

              <button
                type="button"
                onClick={handleSignOut}
                disabled={busy}
                className="text-sm font-semibold text-[#AD573B] underline underline-offset-4 disabled:opacity-50"
              >
                {busy ? "Signing out..." : "Sign Out"}
              </button>
            </div>
          </div>
        ) : (
          <div className="heritage-card mt-10">
            <div className="mb-8 flex gap-6 border-b border-[#252521]/20 pb-5">
              <button
                type="button"
                onClick={() => changeMode("signin")}
                disabled={busy}
                aria-pressed={mode === "signin"}
                className={`text-sm font-bold ${
                  mode === "signin"
                    ? "text-[#AD573B] underline underline-offset-8"
                    : "text-[#777C60]"
                }`}
              >
                Sign In
              </button>

              <button
                type="button"
                onClick={() => changeMode("signup")}
                disabled={busy}
                aria-pressed={mode === "signup"}
                className={`text-sm font-bold ${
                  mode === "signup"
                    ? "text-[#AD573B] underline underline-offset-8"
                    : "text-[#777C60]"
                }`}
              >
                Create Account
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <label
                htmlFor="email"
                className="block text-sm font-semibold"
              >
                Email Address
              </label>

              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                disabled={busy}
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="mt-3 w-full border border-[#D9C6A3] bg-[#FFFDF8] px-4 py-3 outline-none focus:border-[#AD573B]"
              />

              <label
                htmlFor="password"
                className="mt-6 block text-sm font-semibold"
              >
                Password
              </label>

              <input
                id="password"
                type="password"
                autoComplete={
                  mode === "signup" ? "new-password" : "current-password"
                }
                minLength={mode === "signup" ? 8 : undefined}
                required
                disabled={busy}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="mt-3 w-full border border-[#D9C6A3] bg-[#FFFDF8] px-4 py-3 outline-none focus:border-[#AD573B]"
              />

              {mode === "signup" && (
                <p className="mt-2 text-xs text-[#777C60]">
                  Use at least 8 characters.
                </p>
              )}

              <button
                type="submit"
                disabled={busy}
                className="heritage-button mt-8 w-full disabled:cursor-wait disabled:opacity-50"
              >
                {busy
                  ? "Please wait..."
                  : mode === "signup"
                    ? "Create My Account"
                    : "Sign In"}
              </button>
            </form>
          </div>
        )}

        {message && (
          <div
            role="status"
            className="mt-6 border-l-2 border-[#777C60] bg-[#EAE3D5] p-5 text-sm leading-relaxed"
          >
            {message}
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="mt-6 border-l-2 border-[#AD573B] bg-[#EAE3D5] p-5 text-sm leading-relaxed text-[#AD573B]"
          >
            {error}
          </div>
        )}
      </section>
    </main>
  );
}