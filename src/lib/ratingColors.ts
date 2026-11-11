/** Muted, accessible rating colors on the site's cream backgrounds. */
export const RATING_COLORS = [
  "#9B3E35", // 1 — brick red
  "#99532E", // 2 — copper
  "#80621A", // 3 — ochre
  "#5D6C31", // 4 — olive
  "#07472B", // 5 — forest green
] as const;

export function getRatingColor(score: number | null | undefined): string {
  if (typeof score !== "number" || !Number.isFinite(score)) return "#626C57";
  const value = Math.min(5, Math.max(1, score));
  const lower = Math.floor(value) - 1;
  const upper = Math.min(lower + 1, RATING_COLORS.length - 1);
  const weight = value - Math.floor(value);
  const channel = (hex: string, index: number) => parseInt(hex.slice(index, index + 2), 16);
  return "#" + [1, 3, 5].map((index) => {
    const a = channel(RATING_COLORS[lower], index);
    const b = channel(RATING_COLORS[upper], index);
    return Math.round(a + (b - a) * weight).toString(16).padStart(2, "0");
  }).join("").toUpperCase();
}
