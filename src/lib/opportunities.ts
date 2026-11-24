import type { ResearchCoverage } from "./researchCoverage";
import { activeCategoryEvidence, categorySourceTerms, opportunityCategoryStatus, type CategoryEvidence } from "./opportunityCategories";
import { opportunityDeadline } from "./opportunityPresentation";
import { deadlineForInput } from "./opportunityDeadline";
import { firstPublishedTime, isNewlyPosted, isPostedSince } from "./opportunityRecency";
import { comparableBoothFee, publishedPriceOptions, type OpportunityFieldFacts } from "./opportunityFacts";

export const VENDOR_CATEGORIES = ["Food & Beverages", "Food Trucks", "Art & Photography", "Handmade Crafts", "Jewelry & Accessories", "Clothing & Vintage", "Bath, Body & Beauty", "Plants & Farm Products", "Pet Products", "Services", "Other"];
export type Opportunity = {
 access?: "preview" | "example" | "full";
 id: string; title: string; organizer: string; city: string; state: string; venue: string;
 starts_on: string; ends_on: string; schedule_type?: 'dated_event' | 'recurring_season' | 'seasonal_application' | 'rolling_market'; deadline: string | null; application_url: string; source_url: string;
 research_coverage?: ResearchCoverage;
 application_method?: "form" | "email" | "instagram"; application_contact?: string; opens_on?: string | null; deadline_date?: string | null;
 field_facts?: OpportunityFieldFacts;
 category_evidence?: Record<string, CategoryEvidence>;
 categories: string[]; booth_fee: number | null; application_fee: number | null; deposit: number | null;
 fee_notes: string; eligibility: string; verified_at: string | null; published_at?: string | null; effective_status: string;
 occurrence_id: string; market_id: string; market_slug: string;
 history: { review_count: number; reviewer_count: number; overall: number | null };
};
export const statusLabel = (value: string) => ({ open: "Applications open", announced: "Opening soon", limited: "Limited options", waitlist: "Waitlist only", closed: "Closed", needs_recheck: "Needs rechecking", unavailable: "Unavailable" }[value] ?? value);
export function safeExternalUrl(value: string): string | null {
 try { const url = new URL(value); return url.protocol === "https:" && !url.username && !url.password ? url.href : null; } catch { return null; }
}
export type OpportunityFilters = {
 search: string; city: string; month: string; category: string; status: string;
 includeUnconfirmed?: boolean; maxBoothFee?: string; deadlineBefore?: string;
 priceAvailability?: "all" | "published" | "unpublished";
 schedule?: "all" | "dated" | "seasonal" | "ongoing";
 posted?: "all" | "week" | "since";
};
export type OpportunitySort = "date" | "deadline" | "fee_asc" | "rating_desc" | "posted_desc";

export function filterOpportunities(
 items: Opportunity[], filters: OpportunityFilters, lastVisit: string | null = null, now = Date.now(),
) {
 const query = filters.search.trim().toLocaleLowerCase();
 const max = filters.maxBoothFee?.trim() ? Number(filters.maxBoothFee) : null;
 return items.filter(item => {
  if (query && ![item.title,item.organizer,item.city,item.venue,
    ...Object.values(activeCategoryEvidence(item,now)).flatMap(categorySourceTerms)]
    .join(" ").toLocaleLowerCase().includes(query)) return false;
  if (filters.city && item.city !== filters.city) return false;
  if (filters.posted === "week" && !isNewlyPosted(item, now)) return false;
  if (filters.posted === "since" && !isPostedSince(item, lastVisit, now)) return false;
  // ISO calendar dates compare lexically; use the actual month's final day.
  if (filters.month && /^\d{4}-(0[1-9]|1[0-2])$/.test(filters.month)) {
   const [year,month] = filters.month.split("-").map(Number);
   const last = new Date(Date.UTC(year,month,0)).getUTCDate();
   if (item.schedule_type !== "rolling_market" && (item.starts_on > `${filters.month}-${String(last).padStart(2,"0")}` || item.ends_on < `${filters.month}-01`)) return false;
  }
  if (filters.category) {
   // A match is to related source-listed products, never blanket approval.
   const categoryStatus = opportunityCategoryStatus(item,filters.category,now);
   if (categoryStatus !== "eligible" && !(filters.includeUnconfirmed === true && categoryStatus === "unknown")) return false;
  }
  if (filters.status !== "all" && (filters.status === "active"
   ? !["open","limited","waitlist","announced"].includes(item.effective_status) : filters.status !== item.effective_status)) return false;
  if (filters.schedule === "ongoing" && item.schedule_type !== "rolling_market") return false;
  if (filters.schedule === "seasonal" && !["recurring_season","seasonal_application"].includes(item.schedule_type ?? "")) return false;
  if (filters.schedule === "dated" && item.schedule_type !== "dated_event" && item.schedule_type !== undefined) return false;
  const boothPrice=comparableBoothFee(item);
  const hasPublishedPrice=boothPrice !== null || publishedPriceOptions(item,"booth").length>0;
  if (filters.priceAvailability === "published" && !hasPublishedPrice) return false;
  if (filters.priceAvailability === "unpublished" && hasPublishedPrice) return false;
  // Never treat a missing or category-specific fee as a free booth.
  if (max !== null && Number.isFinite(max) && max >= 0 &&
      (boothPrice === null || boothPrice > max)) return false;
  if (filters.deadlineBefore) {
   const deadline = opportunityDeadline(item);
   const cutoff = deadline.sortAt;
   // Unknown / series deadlines are not confirmed to fall before the date.
   if (!/^\d{4}-\d{2}-\d{2}$/.test(filters.deadlineBefore) || !Number.isFinite(cutoff) || ("calendarDate" in deadline ? String(deadline.calendarDate) : deadlineForInput(item.deadline ?? "")) > filters.deadlineBefore) return false;
  }
  return true;
 });
}

export function sortOpportunities(items: Opportunity[], sort: OpportunitySort): Opportunity[] {
 const dateOrder = (a:Opportunity,b:Opportunity) => (a.schedule_type === "rolling_market" ? 1 : 0) - (b.schedule_type === "rolling_market" ? 1 : 0) || a.starts_on.localeCompare(b.starts_on) || a.title.localeCompare(b.title);
 return [...items].sort((a,b) => {
  if (sort === "posted_desc") return (firstPublishedTime(b) ?? 0) - (firstPublishedTime(a) ?? 0) || dateOrder(a,b);
  if (sort === "deadline") return opportunityDeadline(a).sortAt - opportunityDeadline(b).sortAt || dateOrder(a,b);
  if (sort === "fee_asc") return (comparableBoothFee(a) ?? Infinity) - (comparableBoothFee(b) ?? Infinity) || dateOrder(a,b);
  if (sort === "rating_desc") return (b.history.review_count ? (b.history.overall ?? -1) : -1) - (a.history.review_count ? (a.history.overall ?? -1) : -1) || dateOrder(a,b);
  return dateOrder(a,b);
 });
}
export const fee = (amount: number | null) => amount === null ? "Not published" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(Number(amount));
