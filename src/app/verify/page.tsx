"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { createClient } from "../../lib/supabase/client";

type VendorProfile = {
  business_name: string;
  business_url: string | null;
  verification_status: "pending" | "approved" | "rejected";
};

export default function VerifyPage() {
  const [userId, setUserId] = useState<string | null>(null);
  const [profile, setProfile] = useState<VendorProfile | null>(null);
  const [businessName, setBusinessName] = useState("");
  const [businessUrl, setBusinessUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadProfile() {
      try {
        const supabase = createClient();

        const { data: authData, error: authError } =
          await supabase.auth.getUser();

        if (authError) {
          if (authError.name === "AuthSessionMissingError") {
            return;
          }

          throw authError;
        }

        if (!authData.user) return;

        const { data, error } = await supabase
          .from("vendor_profiles")
          .select("business_name, business_url, verification_status")
          .eq("user_id", authData.user.id)
          .maybeSingle();

        if (error) throw error;

        if (active) {
          setUserId(authData.user.id);
          setProfile(data);
        }
      } catch (error) {
        console.error("Unable to load vendor verification:", error);

        if (active) {
          setLoadFailed(true);
          setError(
            "We couldn't load your verification details. Please refresh to try again."
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadProfile();

    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;

    setError("");

    const name = businessName.trim();
    const verificationNotes = notes.trim();
    const website = businessUrl.trim();

    if (!name || !verificationNotes) {
      setError("Please enter your business name and verification details.");
      return;
    }

    if (website) {
      try {
        const url = new URL(website);

        if (url.protocol !== "https:" && url.protocol !== "http:") {
          throw new Error("Invalid website");
        }
      } catch {
        setError(
          "Please enter a full website or social profile URL starting with https:// or http://."
        );
        return;
      }
    }

    setBusy(true);

    try {
      const supabase = createClient();

      const { data: authData, error: authError } =
        await supabase.auth.getUser();

      if (authError || !authData.user) {
        setUserId(null);
        throw new Error("Please sign in again before submitting.");
      }

      const { error } = await supabase
        .from("vendor_profiles")
        .insert({
          user_id: authData.user.id,
          business_name: name,
          business_url: website || null,
          verification_notes: verificationNotes,
        });

      if (error) {
        if (error.code === "23505") {
          throw new Error(
            "An application already exists for your account. Refresh to see its status."
          );
        }

        throw error;
      }

      setProfile({
        business_name: name,
        business_url: website || null,
        verification_status: "pending",
      });

      setNotes("");
    } catch (error) {
      console.error("Unable to submit vendor verification:", error);

      setError(
        error instanceof Error
          ? error.message
          : "We couldn't submit your application. Please try again."
      );
    } finally {
      setBusy(false);
    }
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

          <div className="flex items-center gap-6 text-sm font-semibold">
            <Link href="/markets" className="hover:text-[#AD573B]">
              Explore Markets
            </Link>
            <Link href="/login" className="hover:text-[#AD573B]">
              My Account
            </Link>
          </div>
        </nav>
      </header>

      <section className="mx-auto max-w-2xl px-6 py-16 md:py-24">
        <p className="heritage-label">Trust Behind Every Review</p>

        <h1 className="heritage-heading mt-5 text-4xl md:text-5xl">
          Verify your vendor account.
        </h1>

        <p className="mt-6 leading-relaxed text-[#55554E]">
          Tell us about your business so we can review your vendor
          status. Your application is private and will not appear on
          your public reviews.
        </p>

        {loading ? (
          <p className="mt-10 text-[#55554E]" role="status">
            Loading your verification details...
          </p>
        ) : loadFailed ? (
          <div className="heritage-card mt-10">
            <p className="text-[#55554E]">
              Refresh this page to try loading your application again.
            </p>
          </div>
        ) : !userId ? (
          <div className="heritage-card mt-10">
            <h2 className="font-serif text-2xl font-bold">
              Sign in to get started.
            </h2>
            <p className="mt-4 leading-relaxed text-[#55554E]">
              You need an account before submitting a vendor
              verification application.
            </p>
            <Link
              href="/login"
              className="heritage-button mt-6 inline-block"
            >
              Sign In / Create Account →
            </Link>
          </div>
        ) : profile ? (
          <div className="heritage-card mt-10">
            <p className="heritage-label">
              {profile.verification_status === "approved"
                ? "Approved"
                : profile.verification_status === "rejected"
                  ? "Not Approved"
                  : "Pending Review"}
            </p>

            <h2 className="mt-4 font-serif text-3xl font-bold">
              {profile.business_name}
            </h2>

            <p className="mt-5 leading-relaxed text-[#55554E]">
              {profile.verification_status === "approved"
                ? "Your vendor application has been approved. Review submission will be available once we finish connecting the review form."
                : profile.verification_status === "rejected"
                  ? "Your application was reviewed and was not approved. Application updates and resubmissions are not available yet."
                  : "Your application has been received and is waiting for review. You can return to this page to check its status."}
            </p>

            <Link
              href="/markets"
              className="mt-7 inline-block text-sm font-semibold text-[#AD573B] hover:underline"
            >
              Explore Markets →
            </Link>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="heritage-card mt-10"
          >
            <fieldset disabled={busy} className="min-w-0 space-y-7">
              <legend className="sr-only">
                Vendor verification application
              </legend>

              <div>
                <label
                  htmlFor="business-name"
                  className="block text-sm font-semibold"
                >
                  Business Name
                </label>
                <input
                  id="business-name"
                  type="text"
                  autoComplete="organization"
                  required
                  maxLength={150}
                  value={businessName}
                  onChange={(event) =>
                    setBusinessName(event.target.value)
                  }
                  className="mt-3 w-full border border-[#D9C6A3] bg-[#FFFDF8] px-4 py-3 outline-none focus:border-[#AD573B]"
                />
              </div>

              <div>
                <label
                  htmlFor="business-url"
                  className="block text-sm font-semibold"
                >
                  Website or Business Social Profile
                  <span className="ml-2 text-xs font-normal text-[#777C60]">
                    Optional
                  </span>
                </label>
                <input
                  id="business-url"
                  type="url"
                  maxLength={500}
                  placeholder="https://..."
                  value={businessUrl}
                  onChange={(event) =>
                    setBusinessUrl(event.target.value)
                  }
                  className="mt-3 w-full border border-[#D9C6A3] bg-[#FFFDF8] px-4 py-3 outline-none focus:border-[#AD573B]"
                />
              </div>

              <div>
                <label
                  htmlFor="verification-notes"
                  className="block text-sm font-semibold"
                >
                  Tell Us About Your Vendor Business
                </label>
                <p className="mt-2 text-sm leading-relaxed text-[#55554E]">
                  Describe what you sell and name markets or events
                  you&apos;ve participated in. You can include public
                  links that help us verify your business.
                </p>
                <textarea
                  id="verification-notes"
                  required
                  rows={6}
                  maxLength={2000}
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  className="mt-3 w-full border border-[#D9C6A3] bg-[#FFFDF8] px-4 py-3 outline-none focus:border-[#AD573B]"
                />
                <p className="mt-2 text-right text-xs text-[#777C60]">
                  {notes.length} / 2000 characters
                </p>
              </div>

              <div className="border-l-2 border-[#AD573B] bg-[#EAE3D5] p-4 text-sm leading-relaxed text-[#55554E]">
                These details are for private verification. Do not
                include passwords, payment information, government ID
                numbers, or other sensitive documents.
              </div>

              <button
                type="submit"
                className="heritage-button w-full disabled:cursor-wait disabled:opacity-50"
              >
                {busy ? "Submitting..." : "Submit for Verification"}
              </button>
            </fieldset>
          </form>
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