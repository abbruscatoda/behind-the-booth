// Application deadlines are entered in North Carolina time, independent of the browser timezone.
const formatter = new Intl.DateTimeFormat("en-CA", { timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" });
export function deadlineForInput(value: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "";
  const parts = formatter.formatToParts(date);
  const get = (type: string) => parts.find(part => part.type === type)!.value;
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}:${get("second")}`;
}
export function deadlineForSave(value: string, original = ""): string {
  if (!value) return "";
  // Preserve existing timestamps, including seconds and the repeated fall-back hour.
  if (original && deadlineForInput(original) === value) return original;
  const normalized = value.length === 16 ? `${value}:00` : value;
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(normalized)) throw new Error("Choose a valid application deadline date and time.");
  const base = Date.parse(`${normalized}Z`);
  const matches = [4, 5].map(hours => new Date(base + hours * 3600000)).filter(date => Number.isFinite(date.getTime()) && deadlineForInput(date.toISOString()) === normalized);
  if (matches.length === 0) throw new Error("That Eastern time does not exist. Choose a valid time outside the daylight-saving clock change.");
  if (matches.length > 1) throw new Error("That Eastern time occurs twice during the daylight-saving clock change. Choose a time before 1 AM or at/after 2 AM.");
  return matches[0].toISOString();
}
