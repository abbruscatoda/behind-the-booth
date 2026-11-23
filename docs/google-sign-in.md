# Google sign-in

The login page supports both free signup and sign-in with Google through Supabase Auth. It shows the Google option only when the project's public Auth settings report the Google provider as enabled. Enabling the provider requires no new deployment.

## Google Auth Platform

Use the Behind the Booth Google Cloud project and a **Web application** OAuth client.

- App name: **Behind the Booth**.
- Website / JavaScript origin: `https://www.behindtheboothhq.com`. Add `https://behindtheboothhq.com` if that host is used independently instead of redirecting to www.
- Authorized redirect URI: `https://aofgsfkijqftopvcdtcx.supabase.co/auth/v1/callback`.
- Audience: **External**, published for production so visitors outside a test-user list can sign in.
- Scopes: basic identity only (`openid`, email and profile). No Gmail, Drive, or other Google service access is needed.
- Configure public app branding, support email, and the site's [privacy notice](https://www.behindtheboothhq.com/privacy) in Google. Do not supply a nonexistent terms page.

Store the client ID and client secret in **Supabase → Authentication → Sign In / Providers → Google**, then enable Google and save. Never commit the secret, put it in a `NEXT_PUBLIC_` variable, or share it in chat.

## Supabase URL configuration

Preserve existing email confirmation and password-recovery URLs when editing this list.

- Site URL: `https://www.behindtheboothhq.com`.
- Allowed redirect: `https://www.behindtheboothhq.com/auth/callback`.
- If the bare domain serves the login page independently, allow `https://behindtheboothhq.com/auth/callback` too. Start and finish each flow on the same host so its verifier cookie remains available.
- Keep production redirects specific. Add localhost callbacks only for local testing; avoid broad production wildcards.

The app uses PKCE and its existing cookie-based Supabase client. Its callback exchanges the code, persists the resulting session cookies, and returns to a validated local destination. The return destination uses a short-lived cookie, keeping the callback URL compatible with an exact allowlist. Optional `sb_flow_id` values are supported without enabling the SDK's experimental query-string redirect behavior.

## Verification

1. Check that **Continue with Google** appears on both Sign In and Create Account.
2. Use a new Google identity: confirm the account is created and full member access works, without a separate password or confirmation-email step when Google provides a verified email.
3. Sign out and use Google again: confirm the same account returns, including saved opportunities.
4. Begin from an opportunity or vendor verification link and confirm the intended page opens after sign-in.
5. Cancel Google consent and retry. A failed/expired callback should return to a usable login page without exposing provider errors or tokens.
6. Check a phone layout and a return via the browser's Back button.

Google sign-in does not grant vendor approval or admin access. Supabase manages identity linking; the app does not link accounts based on client-provided email addresses. Existing email/password login and password recovery remain available.

Regression checks: `node --experimental-strip-types --test scripts/test_google_auth.mjs` plus the membership checks in the same GitHub workflow.

`public/google-g.png` is the unmodified official Google logo from `https://developers.google.com/static/identity/images/g-logo.png`, used on the white Google button.

Official setup references: [Supabase Google sign-in](https://supabase.com/docs/guides/auth/social-sign-in/auth-google), [redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls), and [Google button branding](https://developers.google.com/identity/branding-guidelines).
