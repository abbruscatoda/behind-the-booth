import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { AUTH_RETURN_COOKIE, authFailurePath, authReturnPath } from "../../../lib/accountLinks";

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const flowId = request.nextUrl.searchParams.get("sb_flow_id");
  const destination = authReturnPath(request.nextUrl.searchParams.get("next"), request.cookies.get(AUTH_RETURN_COOKIE)?.value);
  const response = NextResponse.redirect(new URL(destination, request.url));
  response.cookies.set(AUTH_RETURN_COOKIE,"",{path:"/auth/callback",maxAge:0,sameSite:"lax",secure:request.nextUrl.protocol==="https:"});

  response.headers.set("Cache-Control", "private, no-store, max-age=0");
  response.headers.set("Pragma", "no-cache");
  response.headers.set("Expires", "0");
  response.headers.set("Referrer-Policy", "no-referrer");
  response.headers.set("X-Robots-Tag", "noindex, nofollow");

  const failed = (cancelled = false) => {
    // Keep any verifier-cookie cleanup supplied by Supabase on the response.
    response.headers.set("Location", new URL(authFailurePath(destination, cancelled), request.url).href);
    return response;
  };
  if (request.nextUrl.searchParams.has("error")) {
    return failed(request.nextUrl.searchParams.get("error") === "access_denied");
  }
  if (!code || code.length > 2048 || (flowId !== null && !/^[a-f0-9]{32}$/.test(flowId))) return failed();

  try {
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
      {
        cookies: {
          getAll() {
            return request.cookies.getAll();
          },
          setAll(cookiesToSet) {
            cookiesToSet.forEach(({ name, value, options }) => {
              response.cookies.set(name, value, options);
            });
          },
        },
      }
    );

    const { data, error } = await supabase.auth.exchangeCodeForSession(code, flowId ? { flowId } : undefined);
    if (error || !data.session || !data.user) return failed();

    return response;
  } catch {
    // Never expose or log authorization codes, cookies, tokens or provider errors.
    return failed();
  }
}
