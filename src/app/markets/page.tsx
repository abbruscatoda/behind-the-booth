
"use client";

import { useState } from "react";
import Link from "next/link";

const markets = [
  {
    id: 1,
    name: "Downtown Raleigh Makers Market",
    city: "Raleigh",
    type: "Makers Market",
    description: "A fictional weekend market featuring local artists and makers.",
  },
  {
    id: 2,
    name: "Cary Community Pop-Up",
    city: "Cary",
    type: "Pop-Up",
    description: "A fictional community shopping event featuring small businesses.",
  },
  {
    id: 3,
    name: "Durham Artisan Festival",
    city: "Durham",
    type: "Festival",
    description: "A fictional festival highlighting handmade goods and local vendors.",
  },
];

export default function MarketsPage() {
  const [search, setSearch] = useState("");

  const filteredMarkets = markets.filter((market) =>
    `${market.name} ${market.city} ${market.type}`
      .toLowerCase()
      .includes(search.toLowerCase())
  );

  return (
    <main className="min-h-screen bg-[#111111] text-white">
      <header className="border-b border-gray-800 px-6 py-6">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Link href="/" className="text-xl font-black">
            BEHIND<span className="text-orange-400">THE</span>BOOTH.
          </Link>
          <Link href="/" className="text-sm text-gray-400 hover:text-white">
            Back to Home
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 py-20">
        <p className="mb-4 font-semibold text-orange-400">
          THE MARKET DIRECTORY
        </p>

        <h1 className="text-5xl font-black tracking-tight md:text-6xl">
          Find your next market.
        </h1>

        <p className="mt-6 max-w-2xl text-lg text-gray-400">
          Explore markets, festivals, and pop-up events around
          Raleigh and the Triangle.
        </p>

        <div className="mt-10">
          <input
            type="search"
            placeholder="Search by market name, city, or event type..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="w-full rounded-xl border border-gray-700 bg-[#222222] px-5 py-4 text-white outline-none focus:border-orange-400"
          />
        </div>

        <p className="mt-5 text-sm text-gray-400">
          Showing {filteredMarkets.length} demonstration markets.
          All listings below are fictional.
        </p>

        <div className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          
{filteredMarkets.map((market) => (
  <Link
    key={market.id}
    href={`/markets/${market.id}`}
    className="block rounded-xl border border-gray-700 bg-[#1c1c1c] p-7 transition hover:border-orange-400 hover:bg-[#252525]"
  >
    <span className="text-xs font-bold uppercase tracking-wider text-orange-400">
      Demo listing · {market.type}
    </span>

    <h2 className="mt-4 text-2xl font-bold">
      {market.name}
    </h2>

    <p className="mt-2 text-sm text-gray-400">
      {market.city}, NC
    </p>

    <p className="mt-5 leading-relaxed text-gray-300">
      {market.description}
    </p>

    <p className="mt-6 border-t border-gray-700 pt-4 text-sm text-gray-500">
      Vendor reviews coming soon
    </p>
  </Link>
))}

        </div>

        {filteredMarkets.length === 0 && (
          <div className="mt-8 rounded-xl border border-gray-700 p-8 text-center text-gray-400">
            No markets match your search.
          </div>
        )}
      </section>
    </main>
  );
}
