import type { ResearchCoverage } from "./researchCoverage";
import { opportunityCategoryStatus, type CategoryEvidence } from "./opportunityCategories";

export const VENDOR_CATEGORIES = ["Food & Beverages", "Food Trucks", "Art & Photography", "Handmade Crafts", "Jewelry & Accessories", "Clothing & Vintage", "Bath, Body & Beauty", "Plants & Farm Products", "Pet Products", "Services", "Other"];
export type Opportunity = {
 id: string; title: string; organizer: string; city: string; state: string; venue: string;
 starts_on: string; ends_on: string; deadline: string | null; application_url: string; source_url: string;
 research_coverage?: ResearchCoverage;
 category_evidence?: Record<string, CategoryEvidence>;
 categories: string[]; booth_fee: number | null; application_fee: number | null; deposit: number | null;
 fee_notes: string; eligibility: string; verified_at: string | null; effective_status: string;
 occurrence_id: string; market_id: string; market_slug: string;
 history: { review_count: number; reviewer_count: number; overall: number | null };
};
export const statusLabel = (value: string) => ({ open: "Applications open", limited: "Limited options", waitlist: "Waitlist only", closed: "Closed", needs_recheck: "Needs rechecking", unavailable: "Unavailable" }[value] ?? value);
export function safeExternalUrl(value: string): string | null {
 try { const url = new URL(value); return url.protocol === "https:" && !url.username && !url.password ? url.href : null; } catch { return null; }
}
export function filterOpportunities(items: Opportunity[], filters: { search: string; city: string; month: string; category: string; status: string; includeUnconfirmed?: boolean }) {
 return items.filter(item => (!filters.search || `${item.title} ${item.organizer} ${item.city}`.toLowerCase().includes(filters.search.toLowerCase().trim()))
  && (!filters.city || item.city === filters.city) && (!filters.month || (item.starts_on <= `${filters.month}-31` && item.ends_on >= `${filters.month}-01`))
  && (!filters.category || (opportunityCategoryStatus(item, filters.category) === "eligible" || (filters.includeUnconfirmed === true && opportunityCategoryStatus(item, filters.category) === "unknown"))) && (filters.status === "all" || (filters.status === "active" ? ["open", "limited"].includes(item.effective_status) : filters.status === item.effective_status)));
}
export const fee = (amount: number | null) => amount === null ? "Not published" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(Number(amount));
