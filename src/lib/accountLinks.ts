/** Only return to supported public screens. Never trust a next= URL as a redirect. */
export const AUTH_RETURN_COOKIE = "btb_auth_return_to";
export function safeReturnPath(value: string | null | undefined): string | null {
  if (!value || value.length > 2400 || !value.startsWith("/") || value.startsWith("//") || /[\\\u0000-\u0020]/.test(value)) return null;
  try {
    const url = new URL(value, "https://www.behindtheboothhq.com");
    if (url.origin !== "https://www.behindtheboothhq.com") return null;
    if (!/^\/(?:opportunities|markets(?:\/[a-zA-Z0-9_-]+)?|verify|login)\/?$/.test(url.pathname)) return null;
    if (url.pathname === "/login" && url.search) return null;
    return url.pathname + url.search + url.hash;
  } catch { return null; }
}

export function accountLink(next = "/opportunities", mode: "signup" | "signin" = "signup"): string {
  return `/login?${new URLSearchParams({mode, next: safeReturnPath(next) ?? "/opportunities"})}`;
}
