
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

const markets = [
  {
    id: "1",
    name: "Downtown Raleigh Makers Market",
    city: "Raleigh",
    type: "Makers Market",
  },
  {
    id: "2",
    name: "Cary Community Pop-Up",
    city: "Cary",
    type: "Pop-Up",
  },
  {
    id: "3",
    name: "Durham Artisan Festival",
    city: "Durham",
    type: "Festival",
  },
];
export function generateStaticParams() {
  return markets.map((market) => ({
    id: market.id,
  }));
}
async function MarketProfileContent({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const market = markets.find((item) => item.id === id);

  if (!market) {
    notFound();
  }

  return (
    <main className="min-h-screen bg-[#111111] text-white">
      <header className="border-b border-gray-800 px-6 py-6">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Link href="/" className="text-xl font-black">
            BEHIND<span className="text-orange-400">THE</span>BOOTH.
          </Link>
          <Link href="/markets" className="text-sm text-gray-400 hover:text-white">
            Back to Markets
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-6 py-20">
        <p className="mb-4 font-semibold text-orange-400">
          DEMONSTRATION MARKET PROFILE
        </p>

        <h1 className="text-4xl font-black md:text-6xl">
          {market.name}
        </h1>

        <p className="mt-5 text-lg text-gray-400">
          {market.city}, North Carolina · {market.type}
        </p>

        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {[
            ["Booth Fee", "Not available"],
            ["Vendor Rating", "No reviews yet"],
            ["Foot Traffic", "Not available"],
          ].map(([label, value]) => (
            <div
              key={label}
              className="rounded-xl border border-gray-700 bg-[#1c1c1c] p-7"
            >
              <p className="text-sm text-gray-400">{label}</p>
              <p className="mt-3 text-xl font-bold">{value}</p>
            </div>
          ))}
        </div>

        <section className="mt-12 rounded-xl border border-gray-700 p-8">
          <h2 className="text-2xl font-bold">Vendor Reviews</h2>
          <p className="mt-4 text-gray-400">
            No vendor reviews have been submitted.
            Verified vendor reviews will appear here in the future.
          </p>
        </section>

        <p className="mt-8 text-sm text-orange-300">
          This is a fictional demonstration listing, not a real event.
        </p>
      </section>
    </main>
  );
}

export default function MarketProfile({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-[#111111] p-12 text-white">
          Loading market profile...
        </main>
      }
    >
      <MarketProfileContent params={params} />
    </Suspense>
  );
}
