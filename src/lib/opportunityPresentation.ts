import { deadlineForInput } from "./opportunityDeadline";

type DeadlineDetails = {
 starts_on: string;
 schedule_type?: string;
 deadline: string | null;
 fee_notes?: string;
 research_coverage?: {deadline?: {status?: string}};
};

export function opportunityDeadline(item: DeadlineDetails) {
  if (item.schedule_type === 'recurring_season' && item.deadline === null) return {
    label: 'Application deadline', value: 'Applications accepted year-round',
    note: 'Applications currently lead to the organizer’s waiting list, not a guaranteed booth. No application deadline is listed.',sortAt: Infinity,
  };
  if (item.schedule_type === 'rolling_market' && item.deadline === null) return {
    label: 'Application window', value: 'Rolling applications',
    note: 'This is an ongoing market, not a confirmed individual date or guaranteed booth. Confirm placement with the organizer.',sortAt: Infinity,
  };
  if (item.schedule_type === 'seasonal_application' && item.deadline === null) return {
    label: 'Application deadline', value: 'Deadline not verified',
    note: 'The organizer lists an active seasonal application, but the cutoff has not been independently verified from all application materials. Check the official form.',sortAt: Infinity,
  };
  // An organizer may publish a day-only deadline without a clock time.
  // Show that confirmed date, but never fabricate a midnight/11:59 PM cutoff
  // or use it as an exact timestamp for deadline sorting/filtering.
  if (item.deadline === null && item.schedule_type === "dated_event") {
    const match = /\b(?:(?:application\s+)?registration|applications?)\s+(?:closes|ends|deadline\s+is)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(20\d{2})\b/i.exec(item.fee_notes ?? "");
    if (match) {
      const monthIndex = ["january","february","march","april","may","june","july","august","september","october","november","december"].indexOf(match[1].toLowerCase());
      const date = new Date(Date.UTC(Number(match[3]),monthIndex,Number(match[2])));
      if (monthIndex >= 0 && date.getUTCFullYear() === Number(match[3]) && date.getUTCMonth() === monthIndex && date.getUTCDate() === Number(match[2])) return {
        label: "Registration deadline",
        value: `${date.toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"})} · time not published`,
        note: /(?:sooner|earlier).{0,20}(?:spots? fill|full)/i.test(item.fee_notes ?? "") ? "Registration may close earlier if spots fill." : "An exact submission time was not published.",
        sortAt: Infinity,
      };
    }
  }
  const timestamp = item.deadline ? Date.parse(item.deadline) : NaN;
  if (!Number.isFinite(timestamp)) return {
    label: "Application deadline", value: "Confirm with organizer", note: "Confirm the cutoff for this date with the organizer.", sortAt: Infinity,
  };
  const formatted = new Date(timestamp).toLocaleString("en-US", {
    timeZone: "America/New_York", dateStyle: "medium", timeStyle: "short",
  });
  const seriesDeadline = /\bseries\b[^.!?]*\bdeadline\b/i.test(item.fee_notes ?? "");
  const afterEventStarts = deadlineForInput(item.deadline!) > item.starts_on;
  const sourceUnconfirmed = item.research_coverage?.deadline?.status === "unconfirmed";
  if (seriesDeadline || afterEventStarts || sourceUnconfirmed) return {
    label: "Application deadline", value: "Confirm with organizer",
    note: `${seriesDeadline ? "Series application deadline" : sourceUnconfirmed ? "Unconfirmed organizer-listed deadline" : "Organizer-listed deadline"}: ${formatted}. This does not confirm the application cutoff for this event date.`,
    sortAt: Infinity,
  };
  return {
    label: "Application deadline", value: formatted,
    note: deadlineForInput(item.deadline!) === item.starts_on ? "The listed deadline falls on the event date. Confirm applications are accepted before the event begins." : "",
    sortAt: timestamp,
  };
}

// Convert the known research-note wording into vendor guidance without changing
// the underlying availability, prices, deadlines, or source records.
export function publicOpportunityCopy(value: string): string {
  return value
    .replace(/^Research found\s+/i, "At the last check, the organizer listed ")
    .replace(/Verify remaining options; do not label generally open\./gi, "Confirm remaining availability with the organizer before applying.")
    .replace(/\bdo not label generally open\.?/gi, "Confirm which booth types are still available.");
}

// The worker publishes both option prices together. Only show a range when its
// minimum agrees with the saved fee; manual edits cannot leave a stale range.
export function opportunityBoothPrice(item: {booth_fee: number | null; fee_notes: string; schedule_type?: string}) {
  // A documented seasonal price must never appear as one universal year-round fee.
  if (item.booth_fee !== null && /displayed (?:booth price|\$[\d.]+) is the winter rate/i.test(item.fee_notes)) {
    const summer = /\$([\d,]+(?:\.\d{1,2})?) per (?:stall|market day).*?summer market day/i.exec(item.fee_notes)
      ?? /\$([\d,]+(?:\.\d{1,2})?) per market day in summer/i.exec(item.fee_notes);
    const money = (v: number) => new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(v);
    return {label:"Winter booth / day",value:money(Number(item.booth_fee)),
      note: summer ? "Summer booth / day: "+money(Number(summer[1].replaceAll(",",""))) : "Seasonal rates vary; see full details."};
  }
  const options = /Table options: half table \$([\d,]+(?:\.\d{1,2})?); full table \$([\d,]+(?:\.\d{1,2})?)\./i.exec(item.fee_notes);
  const money = (value: number) => new Intl.NumberFormat("en-US", {style:"currency", currency:"USD"}).format(value);
  if (options) {
    const half = Number(options[1].replaceAll(",", "")), full = Number(options[2].replaceAll(",", ""));
    if (Number.isFinite(half) && Number.isFinite(full) && half > 0 && full >= half && item.booth_fee !== null && Number(item.booth_fee) === half) {
      return {label:"Table options",value:half === full ? money(half) : `${money(half)}–${money(full)}`,note:`Half table ${money(half)} · Full table ${money(full)}`};
    }
  }
  if (item.booth_fee === null && /(?:no event-specific booth (?:fee|price) was verified|event-specific.{0,80}booth (?:fee|price).{0,40}not (?:verified|confirmed)|amount charged for a booth at this specific.{0,80}remains unverified)/i.test(item.fee_notes)) {
    return {label:"Craft-fair booth fee",value:"Check official form",note:"Exact amount could not be independently verified."};
  }
  const label = item.booth_fee !== null && /craft[- ]fair booth.{0,95}10.{0,18}10.{0,60}per event/i.test(item.fee_notes)
    ? "10 × 10 booth · per event"
    : item.schedule_type === "rolling_market" && /(?:per[- ]event|each market|per market date)/i.test(item.fee_notes)
    ? "Booth fee per event"
    : /event-specific booth fee/i.test(item.fee_notes) ? "Event booth fee" : "Standard booth / table";
  return {label,value:item.booth_fee === null ? "Not verified" : money(Number(item.booth_fee)),note:""};
}

// Turn prose into readable bullets without guessing, truncating, or splitting
// currency decimals, common abbreviations, or conditions joined by semicolons.
export function opportunityDetailBullets(value: string): string[] {
  const copy = publicOpportunityCopy(value).replace(/\r\n?/g, "\n");
  const parts: string[] = [];
  for (const line of copy.split(/\n+/)) {
    let start = 0;
    for (let i = 0; i < line.length; i++) {
      if (!/[.!?]/.test(line[i]) || !/^\s+[A-Z]/.test(line.slice(i + 1))) continue;
      const before = line.slice(start, i + 1);
      if (/\b(?:Mr|Mrs|Ms|Dr|St|Jr|Sr|vs|etc)\.$/i.test(before) || /\b[A-Z]\.$/.test(before) || /\b(?:e\.g|i\.e|U\.S)\.$/i.test(before)) continue;
      parts.push(before.trim());
      start = i + 1;
    }
    const rest = line.slice(start).trim();
    if (rest) parts.push(rest);
  }
  return [...new Set(parts.map(part => part.replace(/^\s*[•]\s*/, "").trim()).filter(Boolean))];
}

export function opportunityDetailSections(item: {fee_notes: string; eligibility: string}) {
  const notes: string[] = [], seen = new Set<string>();
  const redundant = new Set([
    "The official event page lists an active application for this date.",
    "The official organizer links a dated vendor form with enabled submission controls.",
    "Acceptance and category availability are subject to organizer approval; remaining booth spaces are not published.",
    "Other booth types have separate pricing.",
    "Confirm totals with the organizer.",
    "Series application deadline; confirm this event date's cutoff with the organizer.",
    "Confirm on the official application.",
  ]);
  function bullets(value: string) {
    return opportunityDetailBullets(value).flatMap(original => {
      const part = original === "Acceptance is juried; a working form does not guarantee acceptance or category availability." ? "Selection is juried." : original;
      if (redundant.has(part) || seen.has(part)) return [];
      seen.add(part);
      if (part.startsWith("Organizer overview lists a different deadline;")) {notes.push(part);return [];}
      return [part];
    });
  }
  const fees = bullets(item.fee_notes), requirements = bullets(item.eligibility);
  return {fees, requirements, notes};
}
