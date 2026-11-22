export const PREFER_NOT_TO_DISCLOSE = "Prefer not to disclose";

export const reviewVendorCategories = [
  "Food & Beverages",
  "Jewelry & Accessories",
  "Art & Photography",
  "Handmade Crafts",
  "Clothing & Apparel",
  "Bath, Body & Beauty",
  "Home Goods & Décor",
  "Plants & Garden",
  "Farm & Agricultural Products",
  "Pet Products",
  "On-Site Services & Experiences",
  "Other",
  PREFER_NOT_TO_DISCLOSE,
];

export function validReviewCategoryChoice(selected: readonly string[]): boolean {
  return selected.length > 0 && selected.every(category => reviewVendorCategories.includes(category)) &&
    (!selected.includes(PREFER_NOT_TO_DISCLOSE) || selected.length === 1);
}

export function toggleReviewCategory(selected: readonly string[], category: string): string[] {
  if (category === PREFER_NOT_TO_DISCLOSE) {
    return selected.includes(category) ? [] : [category];
  }
  const disclosed = selected.filter(item => item !== PREFER_NOT_TO_DISCLOSE);
  return disclosed.includes(category) ? disclosed.filter(item => item !== category) : [...disclosed, category];
}

/** Withheld categories never contribute to public category tags or counts. */
export function publicReviewCategories(selected: readonly string[]): string[] {
  return selected.includes(PREFER_NOT_TO_DISCLOSE) ? [] : [...selected];
}
