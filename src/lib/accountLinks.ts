/** Only return to supported public screens. Never trust a next= URL as a redirect. */
export const AUTH_RETURN_COOKIE = "btb_auth_return_to";

export function authReturnCookie(next: string | null, secure: boolean): string {
  return `${AUTH_RETURN_COOKIE}=${encodeURIComponent(safeReturnPath(next) ?? "/login")}; Path=/auth/callback; Max-Age=3600; SameSite=Lax${secure ? "; Secure" : ""}`;
}

export function authReturnPath(query: string | null, cookie: string | undefined): string {
  let fromCookie = safeReturnPath(cookie);
  if (!fromCookie && cookie) {
    try { fromCookie = safeReturnPath(decodeURIComponent(cookie)); } catch { /* Ignore malformed cookies. */ }
  }
  return safeReturnPath(query) ?? fromCookie ?? "/login";
}

export function authFailurePath(next: string, cancelled = false): string {
  const params = new URLSearchParams({ auth_error: cancelled ? "cancelled" : "failed" });
  const destination = safeReturnPath(next);
  if (destination && destination !== "/login") params.set("next", destination);
  return `/login?${params}`;
}

export function authFailureMessage(code: string | null): string {
  if (code === "cancelled") return "Google sign-in was canceled. You can try again or use email and password.";
  if (code === "failed") return "We couldn't complete sign-in. Please try again in the same browser. If you used an email confirmation link, it may have expired; try signing in or request a new confirmation email.";
  return "";
}

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
