import { deadlineForInput } from "./opportunityDeadline";

type DeadlineDetails = { starts_on: string; deadline: string | null; fee_notes?: string };

export function opportunityDeadline(item: DeadlineDetails) {
  const timestamp = item.deadline ? Date.parse(item.deadline) : NaN;
  if (!Number.isFinite(timestamp)) return {
    label: "Application deadline", value: "Confirm with organizer", note: "Confirm the cutoff for this date with the organizer.", sortAt: Infinity,
  };
  const formatted = new Date(timestamp).toLocaleString("en-US", {
    timeZone: "America/New_York", dateStyle: "medium", timeStyle: "short",
  });
  const seriesDeadline = /\bseries\b[^.!?]*\bdeadline\b/i.test(item.fee_notes ?? "");
  const afterEventStarts = deadlineForInput(item.deadline!) > item.starts_on;
  if (seriesDeadline || afterEventStarts) return {
    label: "Application deadline", value: "Confirm with organizer",
    note: `${seriesDeadline ? "Series application deadline" : "Organizer-listed deadline"}: ${formatted}. This does not confirm the application cutoff for this event date.`,
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
export function opportunityBoothPrice(item: {booth_fee: number | null; fee_notes: string}) {
  const options = /Table options: half table \$([\d,]+(?:\.\d{1,2})?); full table \$([\d,]+(?:\.\d{1,2})?)\./i.exec(item.fee_notes);
  const money = (value: number) => new Intl.NumberFormat("en-US", {style:"currency", currency:"USD"}).format(value);
  if (options) {
    const half = Number(options[1].replaceAll(",", "")), full = Number(options[2].replaceAll(",", ""));
    if (Number.isFinite(half) && Number.isFinite(full) && half > 0 && full >= half && item.booth_fee !== null && Number(item.booth_fee) === half) {
      return {label:"Table options",value:half === full ? money(half) : `${money(half)}–${money(full)}`,note:`Half table ${money(half)} · Full table ${money(full)}`};
    }
  }
  return {label:"Standard booth / table",value:item.booth_fee === null ? "Not published" : money(Number(item.booth_fee)),note:""};
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
