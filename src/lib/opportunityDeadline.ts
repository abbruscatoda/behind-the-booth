// Current Triangle events use North Carolina's calendar, independent of browser timezone.
const formatter = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" });
function easternTimestamp(value: string): string {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "";
  const parts = formatter.formatToParts(date);
  const get = (type: string) => parts.find(part => part.type === type)!.value;
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}:${get("second")}`;
}
export function deadlineForInput(value: string): string {
  return value ? easternTimestamp(value).slice(0, 10) : "";
}
export function deadlineForSave(value: string, original = ""): string {
  if (!value) return "";
  // Editing other fields must not extend a source's already-known exact cutoff.
  if (original && deadlineForInput(original) === value) return original;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error("Choose a valid application deadline date.");
  const normalized = `${value}T23:59:59`;
  const base = Date.parse(`${normalized}Z`);
  const matches = [4, 5].map(hours => new Date(base + hours * 3600000)).filter(date => Number.isFinite(date.getTime()) && easternTimestamp(date.toISOString()) === normalized);
  if (matches.length !== 1) throw new Error("Choose a valid application deadline date.");
  return matches[0].toISOString();
}
