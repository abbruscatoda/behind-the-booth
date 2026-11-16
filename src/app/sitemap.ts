import type { MetadataRoute } from "next";
import { listPublicMarkets } from "../lib/publicMarkets";
import { SITE_URL } from "../lib/siteMetadata";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const markets = await listPublicMarkets();
  return [
    ...["", "/markets", "/opportunities", "/community-guidelines", "/privacy", "/contact"].map(path => ({ url: `${SITE_URL}${path}` })),
    ...markets.map(market => ({ url: `${SITE_URL}/markets/${encodeURIComponent(market.slug)}` })),
  ];
}
