export function googleSignInRequest(origin: string) {
  return {
    provider: "google" as const,
    options: {
      redirectTo: new URL("/auth/callback", origin).href,
      scopes: "openid email profile",
      queryParams: { prompt: "select_account" },
      skipBrowserRedirect: true,
    },
  };
}

/** Public provider availability only. Google credentials stay in Supabase. */
export async function googleSignInEnabled(signal?: AbortSignal): Promise<boolean> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) return false;
  try {
    const response = await fetch(`${url}/auth/v1/settings`, {
      headers: { apikey: key },
      cache: "no-store",
      signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(8000)]) : AbortSignal.timeout(8000),
    });
    if (!response.ok) return false;
    const settings = await response.json();
    return settings?.external?.google === true;
  } catch {
    // Email sign-in remains available if the provider is disabled or unreachable.
    return false;
  }
}
