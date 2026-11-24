import { VENDOR_CATEGORIES, type OpportunityFilters, type OpportunitySort } from "./opportunities";

export const defaultOpportunityFilters: OpportunityFilters = {
 search: "", city: "", month: "", category: "", status: "active",
 includeUnconfirmed: true, maxBoothFee: "", deadlineBefore: "", priceAvailability: "all", schedule: "all", posted: "all",
};
export const defaultOpportunitySort: OpportunitySort = "date";

const keys = ["q", "city", "month", "category", "status", "unconfirmed", "price", "maxFee", "deadline", "sort", "schedule", "posted"] as const;
const statuses = new Set(["active", "all", "open", "announced", "limited", "waitlist", "needs_recheck", "closed"]);
const sorts = new Set<OpportunitySort>(["date", "deadline", "fee_asc", "rating_desc", "posted_desc"]);
const prices = new Set(["all", "published", "unpublished"]);
const schedules = new Set(["all", "dated", "seasonal", "ongoing"]);
const isoMonth = /^\d{4}-(0[1-9]|1[0-2])$/;
const isoDate = /^\d{4}-(0[1-9]|1[0-2])-([0-2]\d|3[01])$/;
function validDate(value: string) {
 if (!isoDate.test(value)) return false;
 const [y,m,d] = value.split("-").map(Number);
 const parsed = new Date(Date.UTC(y,m-1,d));
 return parsed.getUTCFullYear() === y && parsed.getUTCMonth() === m-1 && parsed.getUTCDate() === d;
}
function validFee(value: string) {
 return /^\d{1,6}(?:\.\d{1,2})?$/.test(value) && Number(value) <= 100000;
}
export function readOpportunitySearch(params: URLSearchParams): {filters: OpportunityFilters; sort: OpportunitySort} {
 const get = (key: string) => (params.get(key) ?? "").slice(0, 160);
 const status = get("status"), price = get("price"), sort = get("sort");
 const month = get("month"), deadline = get("deadline"), maxFee = get("maxFee");
 return {
  filters: {
   ...defaultOpportunityFilters,
   search: get("q").slice(0, 120),
   city: get("city").slice(0, 80),
   month: isoMonth.test(month) ? month : "",
   category: VENDOR_CATEGORIES.includes(get("category")) ? get("category") : "",
   status: statuses.has(status) ? status : "active",
   includeUnconfirmed: get("unconfirmed") !== "0",
   priceAvailability: prices.has(price) ? price as OpportunityFilters["priceAvailability"] : "all",
   schedule: schedules.has(get("schedule")) ? get("schedule") as OpportunityFilters["schedule"] : "all",
   // "Since last visit" is personal to one browser; shared URLs only preserve the 7-day view.
   posted: get("posted") === "week" ? "week" : "all",
   maxBoothFee: validFee(maxFee) ? maxFee : "",
   deadlineBefore: validDate(deadline) ? deadline : "",
  },
  sort: sorts.has(sort as OpportunitySort) ? sort as OpportunitySort : defaultOpportunitySort,
 };
}
export function writeOpportunitySearch(url: URL, filters: OpportunityFilters, sort: OpportunitySort): URL {
 const next = new URL(url.href);
 for (const key of keys) next.searchParams.delete(key);
 const put = (key: string, value: string) => { if (value) next.searchParams.set(key, value); };
 put("q", filters.search.trim().slice(0, 120));
 put("city", filters.city.slice(0, 80));
 if (isoMonth.test(filters.month)) put("month", filters.month);
 if (VENDOR_CATEGORIES.includes(filters.category)) put("category", filters.category);
 if (statuses.has(filters.status) && filters.status !== "active") put("status", filters.status);
 if (filters.includeUnconfirmed === false) put("unconfirmed", "0");
 if (filters.priceAvailability && filters.priceAvailability !== "all" && prices.has(filters.priceAvailability)) put("price", filters.priceAvailability);
 if (filters.maxBoothFee && validFee(filters.maxBoothFee)) put("maxFee", filters.maxBoothFee);
 if (filters.deadlineBefore && validDate(filters.deadlineBefore)) put("deadline", filters.deadlineBefore);
 if (sort !== defaultOpportunitySort && sorts.has(sort)) put("sort", sort);
 if (filters.schedule && filters.schedule !== "all" && schedules.has(filters.schedule)) put("schedule",filters.schedule);
 if (filters.posted === "week") put("posted","week");
 return next;
}
