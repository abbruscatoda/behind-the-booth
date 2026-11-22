export type PriceOption = {
  label: string; amount: number; kind: "booth" | "application" | "addon";
  unit: "day" | "event" | "season" | "program" | "application";
  conditions: string; applicable: boolean; unavailable?: boolean; source_url: string;
};
type FieldProof = {summary: string; source_url: string};
export type OpportunityFieldFacts = {
  checked_at?: string;
  pricing?: FieldProof & {status: "options" | "unconfirmed" | "varies_by_event"};
  pricing_options?: PriceOption[];
  application_fee?: FieldProof & {status: "confirmed" | "options" | "not_listed" | "access_limited"; amount?: number};
  deadline?: FieldProof & {status: "date_only" | "rolling" | "not_listed" | "access_limited"; date?: string; early_close?: boolean};
  categories?: string[];
  requirements?: FieldProof;
  application_access?: string;
};
export type FactListing = {field_facts?: OpportunityFieldFacts; application_fee?: number | null; booth_fee?: number | null};
export const moneyAmount = (n: number) => new Intl.NumberFormat("en-US", {style:"currency",currency:"USD"}).format(n);
export function publishedPriceOptions(item: FactListing, kind: PriceOption["kind"]): PriceOption[] {
  return (item.field_facts?.pricing_options ?? []).filter(option => option.kind === kind && option.applicable === true && Number.isFinite(option.amount) && option.amount >= 0);
}
export function applicationFeePresentation(item: FactListing) {
  const options = publishedPriceOptions(item,"application");
  if (options.length) {
    const amounts = options.map(option => option.amount), min = Math.min(...amounts), max = Math.max(...amounts);
    return {value: min === max ? moneyAmount(min) : `${moneyAmount(min)}–${moneyAmount(max)}`,note: options.map(option => `${option.label}: ${moneyAmount(option.amount)}`).join(" · ")};
  }
  const field=item.field_facts?.application_fee;
  if (field?.status === "confirmed" && typeof field.amount === "number" && Number.isFinite(field.amount) && field.amount >= 0) return {value:moneyAmount(field.amount),note:field.summary};
  if (item.application_fee != null) return {value: moneyAmount(Number(item.application_fee)),note:""};
  return {value:field?.status === "not_listed" ? "Not separately listed" : "Confirm with organizer",note:field?.summary ?? "A separate application charge could not be confirmed. This does not mean applying is free."};
}
export function hasPublishedApplicationFee(item: FactListing): boolean {
  const field=item.field_facts?.application_fee;
  return item.application_fee != null || publishedPriceOptions(item,"application").length>0 ||
    (field?.status === "confirmed" && typeof field.amount === "number" && Number.isFinite(field.amount) && field.amount >= 0);
}
/** A budget match means at least one published day/event option, not every plan. */
export function comparableBoothFee(item: FactListing): number | null {
  const amounts=publishedPriceOptions(item,"booth").filter(option => option.unit === "day" || option.unit === "event").map(option=>option.amount);
  if (!amounts.length && item.booth_fee != null && Number.isFinite(Number(item.booth_fee))) amounts.push(Number(item.booth_fee));
  return amounts.length ? Math.min(...amounts) : null;
}
