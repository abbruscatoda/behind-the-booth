"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { organizerHref, organizerKey, organizerOptions } from "../../lib/marketOrganizers";
import { createClient } from "../../lib/supabase/client";

type Market = {
  id: string;
  slug: string;
  name: string;
  city: string;
  state: string;
  description: string;
  is_sample: boolean;
  organizer: string | null;
};

function MarketDirectory() {
  const params = useSearchParams();
  const router = useRouter();
  const organizer = params.get("organizer") ?? "";
  function selectOrganizer(value: string) {
    const next = new URLSearchParams(params.toString());
    if (value) next.set("organizer", value); else next.delete("organizer");
    router.replace(`/markets${next.size ? `?${next.toString()}` : ""}`, { scroll: false });
  }
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
          .select("id, slug, name, city, state, description, is_sample, organizer")
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

  const organizers = organizerOptions(markets.map(market => market.organizer));
  const selectedOrganizer = organizers.find(name => organizerKey(name) === organizerKey(organizer)) ?? organizer;
  const filteredMarkets = markets.filter(market =>
    (!organizer || organizerKey(market.organizer) === organizerKey(organizer)) &&
    `${market.name} ${market.city} ${market.state} ${market.description} ${market.organizer ?? ""}`
      .toLowerCase().includes(search.trim().toLowerCase())
  );

  return (
    <main className="flex-1 bg-[#F4F0E6] text-[#252521]">
      
      

      
      

      {/* Directory */}
      <section className="mx-auto max-w-6xl px-6 pb-28 pt-20">
        <div className="mb-8 flex items-center gap-4">
          <span className="h-px w-12 bg-[#07472B]" />
          <p className="heritage-label">The Market Directory</p>
        </div>

        <h1 className="heritage-heading max-w-4xl text-5xl md:text-7xl">
          Find your next
          <br />
          <span className="italic text-[#07472B]">great market.</span>
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
            className="mb-4 block text-xs font-bold uppercase tracking-[0.2em] text-[#626C57]"
          >
            Search the Directory
          </label>

          <input
            id="market-search"
            type="search"
            placeholder="Search markets, cities, or organizers..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="w-full border border-[#252521]/30 bg-[#FFFCF6] px-5 py-4 text-[#252521] outline-none transition placeholder:text-[#626C57] focus:border-[#07472B]"
          />

          <div className="mt-5 grid items-end gap-4 sm:grid-cols-[minmax(0,1fr)_auto]">
            <div><label htmlFor="organizer-filter" className="mb-2 block text-xs font-bold uppercase tracking-[0.15em] text-[#626C57]">Filter by organizer</label>
              <select id="organizer-filter" value={selectedOrganizer} disabled={loading || Boolean(error)} onChange={event => selectOrganizer(event.target.value)} className="w-full border border-[#252521]/30 bg-[#FFFCF6] px-4 py-3 outline-none focus:border-[#07472B]">
                <option value="">All organizers</option>
                {organizer && !organizers.some(name => organizerKey(name) === organizerKey(organizer)) && <option value={organizer}>{organizer}</option>}
                {organizers.map(name => <option key={organizerKey(name)} value={name}>{name}</option>)}
              </select>
            </div>
            {(search || organizer) && <button type="button" onClick={() => { setSearch(""); selectOrganizer(""); }} className="px-3 py-3 text-sm font-semibold text-[#07472B] underline underline-offset-4">Clear filters</button>}
          </div>
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
        {markets.some(market => market.is_sample) && <div className="mt-10 border-l-2 border-[#07472B] bg-[#E9E7DA] px-5 py-4">
          <p className="text-sm leading-relaxed text-[#55554E]">
            <strong>Demonstration directory:</strong> Listings marked
            Demo are fictional examples used to test Behind the Booth.
            These are separate from real market listings.
          </p>
        </div>}

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

                <span className="text-xs font-semibold uppercase tracking-wider text-[#626C57]">
                  {market.is_sample ? "Demo" : "Listing"}
                </span>
              </div>

              <div className="my-7 h-px bg-[#252521]/20" />

              <h2 className="font-serif text-3xl font-bold leading-tight">
                {market.name}
              </h2>

              <p className="mt-3 text-sm font-semibold uppercase tracking-wider text-[#626C57]">
                {market.city},{" "}
                {market.state === "NC" ? "North Carolina" : market.state}
              </p>

              {market.organizer && <Link href={organizerHref(market.organizer)} className="mt-4 self-start rounded-sm border border-[#07472B]/25 bg-[#E9E7DA] px-3 py-2 text-xs font-semibold text-[#07472B] hover:underline">Organizer: {market.organizer}</Link>}

              <p className="mt-6 flex-1 leading-relaxed text-[#55554E]">
                {market.description}
              </p>

              <div className="mt-8 border-t border-[#252521]/20 pt-5">
                <Link
                  href={`/markets/${market.slug}`}
                  className="text-sm font-semibold text-[#07472B] hover:underline"
                >
                  View market details →
                </Link>
              </div>
            </article>
          ))}
        </div>

        {!loading && !error && filteredMarkets.length === 0 && (
          <div className="mt-10 border border-[#252521]/20 bg-[#E9E7DA] p-10 text-center">
            <h2 className="font-serif text-2xl font-bold">
              No markets found.
            </h2>
            <p className="mt-3 text-[#55554E]">
              {markets.length === 0
                ? "There are no market listings yet. Check back soon."
                : "Try a different search or clear the organizer filter."}
            </p>
          </div>
        )}
      </section>

      
      
    </main>
  );
}

export default function MarketsPage() {
  return <Suspense fallback={<main className="mx-auto max-w-6xl px-6 py-20"><p role="status">Loading market directory…</p></main>}><MarketDirectory /></Suspense>;
}
