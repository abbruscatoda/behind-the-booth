import { deadlineForInput } from "./opportunityDeadline";

type DeadlineDetails = { starts_on: string; deadline: string | null; fee_notes?: string };

export function opportunityDeadline(item: DeadlineDetails) {
  const timestamp = item.deadline ? Date.parse(item.deadline) : NaN;
  if (!Number.isFinite(timestamp)) return {
    label: "Event-date deadline", value: "Not published", note: "Confirm the cutoff for this date with the organizer.", sortAt: Infinity,
  };
  const formatted = new Date(timestamp).toLocaleString("en-US", {
    timeZone: "America/New_York", dateStyle: "medium", timeStyle: "short",
  }) + " Eastern";
  const seriesDeadline = /\bseries\b[^.!?]*\bdeadline\b/i.test(item.fee_notes ?? "");
  const afterEventStarts = deadlineForInput(item.deadline!) > item.starts_on;
  if (seriesDeadline || afterEventStarts) return {
    label: "Event-date deadline", value: "Confirm with organizer",
    note: `${seriesDeadline ? "Series application deadline" : "Organizer-listed deadline"}: ${formatted}. This does not confirm the application cutoff for this event date.`,
    sortAt: Infinity,
  };
  return {
    label: "Apply by", value: formatted,
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
