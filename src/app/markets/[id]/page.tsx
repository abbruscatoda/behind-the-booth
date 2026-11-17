import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import { getPublicMarket } from "../../../lib/publicMarkets";
import { pageMetadata, isIndexableMarket } from "../../../lib/siteMetadata";
import MarketProfileClient from "./MarketProfileClient";

export const instant = false;

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const market = await getPublicMarket(id);
  if (!market) notFound();
  const title = `${market.name} — ${market.city}, ${market.state}`;
  const description = `${market.name} in ${market.city}, ${market.state}. ${market.description}`.replace(/\s+/g, " ").trim().slice(0, 170);
  return { ...pageMetadata(title, description, `/markets/${encodeURIComponent(market.slug)}`),
    ...(!isIndexableMarket(market) ? { robots: { index: false, follow: false } } : {}) };
}

async function MarketDetails({ params }: Props) {
  const { id } = await params;
  const market = await getPublicMarket(id);
  if (!market) notFound();
  return <MarketProfileClient market={market} />;
}

export default function MarketPage({ params }: Props) {
  return (
    <Suspense fallback={
      <main className="mx-auto max-w-6xl px-6 py-14 sm:px-8">
        <p role="status" className="text-sm text-[#55554E]">Loading market details…</p>
      </main>
    }>
      <MarketDetails params={params} />
    </Suspense>
  );
}


