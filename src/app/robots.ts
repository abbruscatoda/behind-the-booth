import type { MetadataRoute } from "next";
import { SITE_URL } from "../lib/siteMetadata";

export default function robots(): MetadataRoute.Robots {
  // Let crawlers read page-level noindex. robots.txt is not access control.
  return { rules: { userAgent: "*", allow: "/" }, sitemap: `${SITE_URL}/sitemap.xml`, host: SITE_URL };
}
