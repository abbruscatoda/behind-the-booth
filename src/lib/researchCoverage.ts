export const coverageLabels = {
  identity: "Event and application identity",
  availability: "Application status",
  categories: "Vendor categories",
  costs: "Costs and fees",
  requirements: "Vendor requirements",
  deadline: "Event-specific deadline",
} as const;
export type CoverageKey = keyof typeof coverageLabels;
export type CoverageFact = {status: "confirmed" | "partial" | "unconfirmed"; summary: string; source_url: string; checked_at: string};
export type ResearchCoverage = Partial<Record<CoverageKey, CoverageFact>>;
export function currentCoverage(value: ResearchCoverage | undefined, now = Date.now()): [CoverageKey, CoverageFact][] {
  return (Object.keys(coverageLabels) as CoverageKey[]).flatMap(key => {
    const fact = value?.[key];
    if (!fact || !["confirmed", "partial", "unconfirmed"].includes(fact.status) || typeof fact.summary !== "string" || typeof fact.source_url !== "string") return [];
    const checked = Date.parse(fact.checked_at);
    return Number.isFinite(checked) && checked <= now && now - checked < 7 * 86400000 ? [[key, fact] as [CoverageKey, CoverageFact]] : [];
  });
}
export const coverageStatus = {confirmed: "Checked", partial: "Some details found", unconfirmed: "Confirm with organizer"} as const;
