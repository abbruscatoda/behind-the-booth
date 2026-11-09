"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { createClient } from "../../../lib/supabase/client";

type Market = {
  id: string;
  slug: string;
  name: string;
  city: string;
  state: string;
  description: string;
  is_sample: boolean;
};

const details = [
  {
    label: "Booth Fee",
    value: "Not available",
    note: "Awaiting verified information",
  },
  {
    label: "Vendor Rating",
    value: "Not available",
    note: "Vendor reviews coming soon",
  },
  {
    label: "Foot Traffic",
    value: "Not available",
    note: "Vendor insights coming soon",
  },
];

export default function MarketProfile() {
  const { id } = useParams<{ id: string }>();
  const [market, setMarket] = useState<Market | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadMarket() {
      setLoading(true);
      setError(null);
      setMarket(null);

      try {
        const supabase = createClient();

        const { data, error } = await supabase
          .from("markets")
          .select("id, slug, name, city, state, description, is_sample")
          .eq("slug", id)
          .maybeSingle();

        if (error) throw error;

        if (active) {
          setMarket(data);
        }
      } catch (error) {
        console.error("Unable to load market:", error);

        if (active) {
          setError(
            "We couldn't load this market. Please refresh to try again."
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadMarket();

    return () => {
      active = false;
    };
  }, [id]);

  return (
    <main className="min-h-screen bg-[#F4F0E6] text-[#252521]">
      {/* Announcement */}
      <div className="bg-[#252521] px-5 py-3 text-center text-xs font-semibold uppercase tracking-[0.2em] text-[#F4F0E6]">
        An independent resource for the vendor community
      </div>

      {/* Navigation */}
      <header className="border-b border-[#252521]/20">
        <nav className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-5 px-6 py-7">
          <Link
            href="/"
            className="font-serif text-2xl font-black tracking-tight md:text-3xl"
          >
            Behind the Booth<span className="text-[#AD573B]">.</span>
          </Link>

          <div className="flex items-center gap-7 text-sm font-semibold">
            <Link href="/" className="hover:text-[#AD573B]">
              Home
            </Link>
            <Link href="/markets" className="hover:text-[#AD573B]">
              All Markets
            </Link>
          </div>
        </nav>
      </header>

      <section className="mx-auto max-w-6xl px-6 pb-20 pt-16">
        <Link
          href="/markets"
          className="text-sm font-semibold text-[#AD573B] hover:underline"
        >
          ← Back to Market Directory
        </Link>

        {loading && (
          <p className="mt-14 text-lg text-[#55554E]" role="status">
            Loading market profile...
          </p>
        )}

        {!loading && error && (
          <div
            className="mt-14 border border-[#252521]/20 bg-[#EAE3D5] p-8"
            role="alert"
          >
            <h1 className="font-serif text-3xl font-bold">
              Unable to load market
            </h1>
            <p className="mt-4 text-[#55554E]">{error}</p>
          </div>
        )}

        {!loading && !error && !market && (
          <div className="mt-14 border border-[#252521]/20 bg-[#EAE3D5] p-8">
            <h1 className="font-serif text-3xl font-bold">
              Market not found
            </h1>
            <p className="mt-4 text-[#55554E]">
              We couldn&apos;t find a market at this address. Return to
              the directory to explore available listings.
            </p>
          </div>
        )}

        {!loading && !error && market && (
          <>
            {/* Profile heading */}
            <div className="mt-14 flex items-center gap-4">
              <span className="h-px w-12 bg-[#AD573B]" />
              <p className="heritage-label">Market Field Report</p>
            </div>

            <h1 className="heritage-heading mt-7 max-w-5xl text-5xl md:text-7xl">
              {market.name}
            </h1>

            <p className="mt-6 text-sm font-bold uppercase tracking-[0.16em] text-[#777C60]">
              {market.city},{" "}
              {market.state === "NC" ? "North Carolina" : market.state}
              {" · "}Market / Event
            </p>

            <p className="mt-8 max-w-3xl text-lg leading-relaxed text-[#55554E]">
              {market.description}
            </p>

            {/* Demo disclaimer */}
            {market.is_sample && (
              <div className="mt-12 border-l-2 border-[#AD573B] bg-[#EAE3D5] px-6 py-5">
                <p className="text-sm leading-relaxed text-[#55554E]">
                  <strong>Demonstration profile:</strong> This is a
                  fictional event created to test Behind the Booth.
                  It is not a real market.
                </p>
              </div>
            )}

            {/* Market details */}
            <div className="mt-16">
              <p className="heritage-label">At a Glance</p>

              <h2 className="heritage-heading mt-4 text-3xl md:text-4xl">
                The Market Details
              </h2>

              <div className="mt-8 grid gap-6 md:grid-cols-3">
                {details.map((detail) => (
                  <div key={detail.label} className="heritage-card">
                    <p className="heritage-label">{detail.label}</p>

                    <p className="mt-6 font-serif text-2xl font-bold">
                      {detail.value}
                    </p>

                    <p className="mt-3 text-sm text-[#777C60]">
                      {detail.note}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Vendor reviews */}
            <section className="mt-20 border-t border-[#252521]/25 pt-14">
              <p className="heritage-label">From Behind the Booth</p>

              <h2 className="heritage-heading mt-4 text-4xl">
                Vendor Reviews
              </h2>

              <div className="mt-10 border border-[#252521]/20 bg-[#EAE3D5] px-8 py-14 text-center">
                <div
                  aria-hidden="true"
                  className="mx-auto mb-6 flex h-14 w-14 items-center justify-center rounded-full border border-[#AD573B] font-serif text-3xl italic text-[#AD573B]"
                >
                  B
                </div>

                <h3 className="font-serif text-3xl font-bold">
                  Every vendor has a story.
                </h3>

                <p className="mx-auto mt-5 max-w-xl leading-relaxed text-[#55554E]">
                  Vendor reviews will help tell the story behind each
                  market, from organization and foot traffic to overall
                  value and experience.
                </p>

                <p className="mt-7 text-sm font-semibold text-[#AD573B]">
                  Review submission and verified vendor reviews coming
                  soon.
                </p>
              </div>
            </section>
          </>
        )}
      </section>

      {/* Footer */}
      <footer className="bg-[#252521] px-6 py-12 text-[#F4F0E6]">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-6">
          <div>
            <p className="font-serif text-2xl font-bold">
              Behind the Booth.
            </p>
            <p className="mt-2 text-sm text-[#C7C0B3]">
              A better view from behind the booth.
            </p>
          </div>

          <p className="text-sm text-[#C7C0B3]">
            © 2026 Behind the Booth.
          </p>
        </div>
      </footer>
    </main>
  );
}