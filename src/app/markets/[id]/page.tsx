import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPublicMarket, listPublicMarkets } from "../../../lib/publicMarkets";
import { pageMetadata, isIndexableMarket } from "../../../lib/siteMetadata";
import MarketProfileClient from "./MarketProfileClient";

type Props = { params: Promise<{ id: string }> };

export async function generateStaticParams() {
  const markets = await listPublicMarkets();
  return markets.map(market => ({ id: market.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const market = await getPublicMarket(id);
  if (!market) notFound();
  const title = `${market.name} — ${market.city}, ${market.state}`;
  const description = `${market.name} in ${market.city}, ${market.state}. ${market.description}`.replace(/\s+/g, " ").trim().slice(0, 170);
  return { ...pageMetadata(title, description, `/markets/${encodeURIComponent(market.slug)}`),
    ...(!isIndexableMarket(market) ? { robots: { index: false, follow: false } } : {}) };
}

export default async function MarketPage({ params }: Props) {
  const { id } = await params;
  const market = await getPublicMarket(id);
  if (!market) notFound();
  return <MarketProfileClient market={market} />;
}
