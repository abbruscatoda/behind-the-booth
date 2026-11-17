import type { Opportunity } from "./opportunities";

export type CategoryEvidence = {
  status: "eligible" | "excluded" | "unavailable" | "separate_application";
  note: string;
  source_url: string;
  checked_at: string;
};

export const categoryStatusLabel = {
  eligible: "Organizer lists this category",
  excluded: "Not accepted for this application",
  unavailable: "No spaces listed for this category",
  separate_application: "Separate application required",
} as const;

export function activeCategoryEvidence(item: Opportunity, now = Date.now()): Record<string, CategoryEvidence> {
  return Object.fromEntries(Object.entries(item.category_evidence ?? {}).filter(([, evidence]) => {
    if (!evidence || !Object.hasOwn(categoryStatusLabel, evidence.status) || typeof evidence.checked_at !== "string") return false;
    const checked = Date.parse(evidence.checked_at);
    return Number.isFinite(checked) && checked <= now && now - checked < 7 * 86400000;
  }));
}

export function opportunityCategoryStatus(item: Opportunity, category: string, now = Date.now()) {
  const evidence = activeCategoryEvidence(item, now);
  if (evidence[category]) return evidence[category].status;
  if (item.categories.includes(category)) return "eligible";
  // A researched subset is not a complete list: all remaining categories stay
  // unknown. Preserve the older explicit-list behavior for legacy records.
  if (Object.keys(evidence).length || item.categories.length === 0) return "unknown";
  return "excluded";
}

export function listedOpportunityCategories(item: Opportunity, now = Date.now()) {
  const evidence = activeCategoryEvidence(item, now);
  const listed = item.categories.filter(category => !evidence[category] || evidence[category].status === "eligible");
  return [...new Set([...listed, ...Object.keys(evidence).filter(category => evidence[category].status === "eligible")])];
}
