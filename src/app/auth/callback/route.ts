import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

function confirmationFailed() {
  return new NextResponse(
    "We couldn't complete your email confirmation. The link may have expired or already been used. Return to the website and try signing in. If needed, request a new confirmation email. Open the link in the same browser you used to sign up.",
    {
      status: 400,
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-store",
      },
    }
  );
}

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");

  if (!code || request.nextUrl.searchParams.has("error")) {
    return confirmationFailed();
  }

  const response = NextResponse.redirect(
    new URL("/markets", request.url)
  );

  response.headers.set("Cache-Control", "private, no-store");
  response.headers.set("Pragma", "no-cache");
  response.headers.set("Expires", "0");

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

    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (error) {
      return confirmationFailed();
    }

    return response;
  } catch {
    return confirmationFailed();
  }
}