import type { Metadata } from "next";

export const SITE_URL = "https://www.behindtheboothhq.com";
export const SITE_DESCRIPTION = "Explore Raleigh and Triangle markets. Read anonymous reviews from verified vendors about booth value, foot traffic, organization, and more.";

export function pageMetadata(title: string, description: string, path: string): Metadata {
  const url = `${SITE_URL}${path}`;
  const shareTitle = `${title} | Behind the Booth`;
  return {
    title: { absolute: shareTitle }, description,
    alternates: { canonical: url },
    openGraph: { type: "website", locale: "en_US", siteName: "Behind the Booth", title: shareTitle, description, url,
      images: [{ url: `${SITE_URL}/share/behind-the-booth.png`, width: 1200, height: 630, alt: "Behind the Booth — Know the market before you book the booth." }] },
    twitter: { card: "summary_large_image", title: shareTitle, description, images: [`${SITE_URL}/share/behind-the-booth.png`] },
  };
}

export function isIndexableMarket(market: { is_sample: boolean; name: string }): boolean {
  return !market.is_sample && !/^test(?:\s+only)?\s*[-—:]/i.test(market.name.trim());
}
