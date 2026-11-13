/** Organizer names are public, admin-assigned market metadata. */
export function cleanOrganizer(value: string | null | undefined): string {
  return (value ?? "").replace(/\s+/g, " ").trim();
}
export function organizerKey(value: string | null | undefined): string {
  return cleanOrganizer(value).toLowerCase();
}
export function organizerOptions(values: (string | null | undefined)[]): string[] {
  const names = new Map<string, string>();
  for (const value of values) {
    const name = cleanOrganizer(value);
    if (name && !names.has(organizerKey(name))) names.set(organizerKey(name), name);
  }
  return [...names.values()].sort((a, b) => a.localeCompare(b));
}
export function organizerHref(value: string): string {
  return `/markets?${new URLSearchParams({ organizer: cleanOrganizer(value) }).toString()}`;
}
