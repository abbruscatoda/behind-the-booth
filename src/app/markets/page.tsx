"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { createClient } from "../../lib/supabase/client";

type Market = {
  id: string;
  slug: string;
  name: string;
  city: string;
  state: string;
  description: string;
  is_sample: boolean;
};

export default function MarketsPage() {
  const [search, setSearch] = useState("");
  const [markets, setMarkets] = useState<Market[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadMarkets() {
      try {
        const supabase = createClient();

        const { data, error } = await supabase
          .from("markets")
          .select("id, slug, name, city, state, description, is_sample")
          .order("name");

        if (error) throw error;

        if (active) {
          setMarkets(data ?? []);
        }
      } catch (error) {
        console.error("Unable to load markets:", error);

        if (active) {
          setError(
            "We couldn't load the markets. Please refresh to try again."
          );
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadMarkets();

    return () => {
      active = false;
    };
  }, []);

  const filteredMarkets = markets.filter((market) =>
    `${market.name} ${market.city} ${market.state} ${market.description}`
      .toLowerCase()
      .includes(search.trim().toLowerCase())
  );

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
            <Link
              href="/markets"
              aria-current="page"
              className="text-[#AD573B]"
            >
              Explore Markets
            </Link>
          </div>
        </nav>
      </header>

      {/* Directory */}
      <section className="mx-auto max-w-6xl px-6 pb-28 pt-20">
        <div className="mb-8 flex items-center gap-4">
          <span className="h-px w-12 bg-[#AD573B]" />
          <p className="heritage-label">The Market Directory</p>
        </div>

        <h1 className="heritage-heading max-w-4xl text-5xl md:text-7xl">
          Find your next
          <br />
          <span className="italic text-[#AD573B]">great market.</span>
        </h1>

        <p className="mt-8 max-w-2xl text-lg leading-relaxed text-[#55554E]">
          Explore markets, festivals, and pop-up events around Raleigh
          and the Triangle. Every opportunity starts with better
          information.
        </p>

        {/* Search */}
        <div className="mt-14 border-y border-[#252521]/20 py-8">
          <label
            htmlFor="market-search"
            className="mb-4 block text-xs font-bold uppercase tracking-[0.2em] text-[#777C60]"
          >
            Search the Directory
          </label>

          <input
            id="market-search"
            type="search"
            placeholder="Search markets, cities, or descriptions..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="w-full border border-[#252521]/30 bg-[#FFFDF8] px-5 py-4 text-[#252521] outline-none transition placeholder:text-[#777C60] focus:border-[#AD573B]"
          />

          <p
            className="mt-4 text-sm text-[#55554E]"
            role="status"
            aria-live="polite"
          >
            {loading
              ? "Loading markets..."
              : error
                ? error
                : `Showing ${filteredMarkets.length} ${
                    filteredMarkets.length === 1 ? "market" : "markets"
                  }.`}
          </p>
        </div>

        {/* Demo notice */}
        <div className="mt-10 border-l-2 border-[#AD573B] bg-[#EAE3D5] px-5 py-4">
          <p className="text-sm leading-relaxed text-[#55554E]">
            <strong>Demonstration directory:</strong> Listings marked
            Demo are fictional examples used to test Behind the Booth.
            Real listings and verified vendor reviews will be added
            later.
          </p>
        </div>

        {/* Market cards */}
        <div
          className="mt-10 grid gap-6 md:grid-cols-2 lg:grid-cols-3"
          aria-busy={loading}
        >
          {filteredMarkets.map((market) => (
            <article
              key={market.id}
              className="heritage-card flex flex-col"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="heritage-label">Market / Event</span>

                <span className="text-xs font-semibold uppercase tracking-wider text-[#777C60]">
                  {market.is_sample ? "Demo" : "Listing"}
                </span>
              </div>

              <div className="my-7 h-px bg-[#252521]/20" />

              <h2 className="font-serif text-3xl font-bold leading-tight">
                {market.name}
              </h2>

              <p className="mt-3 text-sm font-semibold uppercase tracking-wider text-[#777C60]">
                {market.city},{" "}
                {market.state === "NC" ? "North Carolina" : market.state}
              </p>

              <p className="mt-6 flex-1 leading-relaxed text-[#55554E]">
                {market.description}
              </p>

              <div className="mt-8 border-t border-[#252521]/20 pt-5">
                <Link
                  href={`/markets/${market.slug}`}
                  className="text-sm font-semibold text-[#AD573B] hover:underline"
                >
                  View market details →
                </Link>
              </div>
            </article>
          ))}
        </div>

        {!loading && !error && filteredMarkets.length === 0 && (
          <div className="mt-10 border border-[#252521]/20 bg-[#EAE3D5] p-10 text-center">
            <h2 className="font-serif text-2xl font-bold">
              No markets found.
            </h2>
            <p className="mt-3 text-[#55554E]">
              {markets.length === 0
                ? "There are no market listings yet. Check back soon."
                : "Try searching for a different market, city, or description."}
            </p>
          </div>
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