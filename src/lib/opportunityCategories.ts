import type { Opportunity } from "./opportunities";

export type CategoryEvidence = {
  status: "eligible" | "excluded" | "unavailable" | "separate_application";
  note: string;
  source_url: string;
  checked_at: string;
  application_state?: "open" | "limited" | "waitlist" | "closed" | "unknown";
  application_deadline?: string;
};

export const categoryStatusLabel = {
  eligible: "Organizer lists this category",
  excluded: "Not accepted for this application",
  unavailable: "Category option unavailable",
  separate_application: "Separate application — confirm availability",
} as const;

export function activeCategoryEvidence(item: Opportunity, now = Date.now()): Record<string, CategoryEvidence> {
  return Object.fromEntries(Object.entries(item.category_evidence ?? {}).filter(([, evidence]) => {
    if (!evidence || !Object.hasOwn(categoryStatusLabel, evidence.status) || typeof evidence.checked_at !== "string") return false;
    const checked = Date.parse(evidence.checked_at);
    return Number.isFinite(checked) && checked <= now && now - checked < 7 * 86400000;
  }).map(([category, evidence]) => {
    const deadline = evidence.application_deadline ? Date.parse(evidence.application_deadline) : NaN;
    return [category, evidence.application_state && evidence.application_state !== "closed" && Number.isFinite(deadline) && deadline <= now
      ? {...evidence, status: "unavailable", application_state: "closed", note: "The separate food-truck application deadline has passed; the main vendor application has its own status."}
      : evidence];
  }));
}

export function opportunityCategoryStatus(item: Opportunity, category: string, now = Date.now()) {
  const evidence = activeCategoryEvidence(item, now);
  if (evidence[category]) return evidence[category].status;
  if (item.categories.includes(category)) return "eligible";
  // All lists are partial. Only an explicit, fresh category fact can exclude a
  // type; absence from either a manual list or researched subset is unknown.
  return "unknown";
}

export function listedOpportunityCategories(item: Opportunity, now = Date.now()) {
  const evidence = activeCategoryEvidence(item, now);
  const listed = item.categories.filter(category => !evidence[category] || evidence[category].status === "eligible");
  return [...new Set([...listed, ...Object.keys(evidence).filter(category => evidence[category].status === "eligible")])];
}

export function categoryEvidenceLabel(entry: CategoryEvidence) {
  if (entry.application_state) return {
    open: "Separate application — open",
    limited: "Separate application — limited options",
    waitlist: "Separate application — waitlist only",
    closed: "Separate application — closed",
    unknown: "Separate application — confirm availability",
  }[entry.application_state];
  return categoryStatusLabel[entry.status];
}

export function categoryHighlights(item: Opportunity, now = Date.now()) {
  return Object.entries(activeCategoryEvidence(item, now)).filter(([, entry]) =>
    entry.status !== "eligible" || /prior organizer discussion|prior approval|ask about freshly prepared/i.test(entry.note));
}
