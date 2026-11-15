import "server-only";
import { cacheLife } from "next/cache";
import { isIndexableMarket } from "./siteMetadata";

export type PublicMarket = { id: string; slug: string; name: string; city: string; state: string; description: string; is_sample: boolean; organizer: string | null };

async function requestMarkets(params: URLSearchParams): Promise<PublicMarket[]> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) throw new Error("Public Supabase connection is not configured.");
  // Only public listing fields, with the existing public key and RLS. No user
  // cookies, service-role key, review content, or verification data on this path.
  const response = await fetch(`${url.replace(/\/$/, "")}/rest/v1/markets?${params}`, {
    headers: { apikey: key },
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new Error(`Public market lookup failed (${response.status}).`);
  return response.json();
}
const fields = "id,slug,name,city,state,description,is_sample,organizer";

export async function getPublicMarket(slug: string): Promise<PublicMarket | null> {
  "use cache";
  cacheLife({ stale: 60, revalidate: 300, expire: 3600 });
  if (!slug || slug.length > 200) return null;
  const rows = await requestMarkets(new URLSearchParams({ select: fields, slug: `eq.${slug}`, limit: "1" }));
  return rows[0] ?? null;
}

export async function listPublicMarkets(): Promise<PublicMarket[]> {
  "use cache";
  cacheLife({ stale: 60, revalidate: 300, expire: 3600 });
  const markets: PublicMarket[] = [];
  for (let offset = 0; ; offset += 1000) {
    const batch = await requestMarkets(new URLSearchParams({ select: fields, is_sample: "eq.false", order: "slug", limit: "1000", offset: String(offset) }));
    markets.push(...batch);
    if (batch.length < 1000) return markets.filter(isIndexableMarket);
  }
}
