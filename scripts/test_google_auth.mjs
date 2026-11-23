import { after, test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import ts from 'typescript';
import { createServerClient } from '@supabase/ssr';
import { NextRequest } from 'next/server.js';
import * as accountLinks from '../src/lib/accountLinks.ts';
import { googleSignInEnabled, googleSignInRequest } from '../src/lib/googleAuth.ts';

// Execute the actual Next route with its real SDK; only HTTP is replaced.
const sourceUrl = new URL('../src/app/auth/callback/route.ts', import.meta.url);
const code = ts.transpileModule(await readFile(sourceUrl, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const require = createRequire(sourceUrl);
const routeModule = { exports: {} };
new Function('require', 'module', 'exports', code)(
  name => name === '../../../lib/accountLinks' ? accountLinks : require(name),
  routeModule, routeModule.exports,
);
const { GET } = routeModule.exports;
const origin = 'https://www.behindtheboothhq.com';
const authUrl = 'https://fixture-project.supabase.co';
const originalFetch = globalThis.fetch;
const env = {
  url: process.env.NEXT_PUBLIC_SUPABASE_URL,
  key: process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
};
process.env.NEXT_PUBLIC_SUPABASE_URL = authUrl;
process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY = 'fixture-public-key';
after(() => {
  globalThis.fetch = originalFetch;
  for (const [key, value] of [
    ['NEXT_PUBLIC_SUPABASE_URL', env.url], ['NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY', env.key],
  ]) { if (value === undefined) delete process.env[key]; else process.env[key] = value; }
});

async function startFlow({ appendFlowId = false } = {}) {
  const cookies = new Map();
  const supabase = createServerClient(authUrl, 'fixture-public-key', {
    auth: { experimental: { appendPkceFlowIdToRedirects: appendFlowId } },
    cookies: {
      getAll: () => [...cookies].map(([name, value]) => ({ name, value })),
      setAll: values => values.forEach(({ name, value }) => cookies.set(name, value)),
    },
  });
  const { data, error } = await supabase.auth.signInWithOAuth(googleSignInRequest(origin));
  assert.equal(error, null);
  return { cookies, authorization: new URL(data.url) };
}
function callback(query = '', cookies = new Map()) {
  return GET(new NextRequest(`${origin}/auth/callback${query}`, {
    headers: { cookie: [...cookies].map(([key, value]) => `${key}=${value}`).join('; ') },
  }));
}
function assertPrivate(response) {
  assert.match(response.headers.get('cache-control'), /private.*no-store/);
  assert.equal(response.headers.get('referrer-policy'), 'no-referrer');
  assert.equal(response.cookies.get(accountLinks.AUTH_RETURN_COOKIE)?.maxAge, 0);
}
function tokenFetch(inspect, { fail = false } = {}) {
  globalThis.fetch = async (url, options) => {
    assert.equal(String(url), `${authUrl}/auth/v1/token?grant_type=pkce`);
    assert.equal(options.method, 'POST');
    inspect(JSON.parse(options.body));
    if (fail) return Response.json({ error_code: 'bad_code_verifier', msg: 'Private provider detail' }, { status: 400 });
    const now = Math.floor(Date.now() / 1000);
    const user = {
      id: '11111111-1111-4111-8111-111111111111', aud: 'authenticated', role: 'authenticated',
      email: 'member@example.test', email_confirmed_at: new Date().toISOString(),
      app_metadata: { provider: 'google', providers: ['google'] }, user_metadata: {},
    };
    const accessToken = [
      { alg: 'HS256', typ: 'JWT' }, { sub: user.id, role: 'authenticated', exp: now + 3600 },
    ].map(value => Buffer.from(JSON.stringify(value)).toString('base64url')).join('.') + '.fixture';
    return Response.json({ access_token: accessToken, refresh_token: 'fixture-refresh',
      token_type: 'bearer', expires_in: 3600, user });
  };
}

test('Google PKCE sign-in returns a session cookie to the selected local page', async () => {
  const { cookies, authorization } = await startFlow();
  assert.equal(authorization.searchParams.get('provider'), 'google');
  assert.equal(authorization.searchParams.get('scopes'), 'openid email profile');
  assert.equal(authorization.searchParams.get('prompt'), 'select_account');
  assert.equal(authorization.searchParams.get('redirect_to'), `${origin}/auth/callback`);
  assert.equal(authorization.searchParams.get('code_challenge_method'), 's256');
  cookies.set(accountLinks.AUTH_RETURN_COOKIE, encodeURIComponent('/opportunities?city=Raleigh#next-market'));
  let exchanges = 0;
  tokenFetch(body => {
    exchanges++;
    assert.equal(body.auth_code, 'fixture-code');
    assert.equal(createHash('sha256').update(body.code_verifier).digest('base64url'), authorization.searchParams.get('code_challenge'));
  });
  const response = await callback('?code=fixture-code', cookies);
  assert.equal(exchanges, 1);
  assert.equal(response.headers.get('location'), `${origin}/opportunities?city=Raleigh#next-market`);
  assert(response.cookies.getAll().some(cookie => cookie.name.startsWith('sb-') && cookie.value && cookie.maxAge > 0));
  assertPrivate(response);
});

test('opt-in flow IDs use the matching verifier cookie', async () => {
  const { cookies, authorization } = await startFlow({ appendFlowId: true });
  const redirect = new URL(authorization.searchParams.get('redirect_to'));
  const flowId = redirect.searchParams.get('sb_flow_id');
  assert.match(flowId, /^[a-f0-9]{32}$/);
  let exchanges = 0;
  tokenFetch(() => exchanges++);
  const response = await callback(`?code=email-fixture&sb_flow_id=${flowId}&next=%2Fverify`, cookies);
  assert.equal(exchanges, 1);
  assert.equal(response.headers.get('location'), `${origin}/verify`);
  assertPrivate(response);
});

test('email signup confirmation still exchanges its verifier and restores its destination', async () => {
  const cookies = new Map([[accountLinks.AUTH_RETURN_COOKIE, encodeURIComponent('/verify')]]);
  globalThis.fetch = async (url, options) => {
    const request = new URL(url);
    assert.equal(request.origin, authUrl);
    assert.equal(request.pathname, '/auth/v1/signup');
    assert.equal(request.searchParams.get('redirect_to'), `${origin}/auth/callback`);
    assert.equal(options.method, 'POST');
    assert.equal(JSON.parse(options.body).code_challenge_method, 's256');
    return Response.json({ id: '11111111-1111-4111-8111-111111111111', email: 'member@example.test' });
  };
  const supabase = createServerClient(authUrl, 'fixture-public-key', {
    cookies: {
      getAll: () => [...cookies].map(([name, value]) => ({ name, value })),
      setAll: values => values.forEach(({ name, value }) => cookies.set(name, value)),
    },
  });
  const { error } = await supabase.auth.signUp({ email: 'member@example.test', password: 'fixture-password',
    options: { emailRedirectTo: `${origin}/auth/callback` } });
  assert.equal(error, null);
  let exchanges = 0;
  tokenFetch(body => { exchanges++; assert.equal(body.auth_code, 'email-confirmation-fixture'); });
  const response = await callback('?code=email-confirmation-fixture', cookies);
  assert.equal(exchanges, 1);
  assert.equal(response.headers.get('location'), `${origin}/verify`);
  assertPrivate(response);
});

test('cancellation and malformed callbacks return a usable login without contacting Auth', async () => {
  globalThis.fetch = async () => { assert.fail('Malformed callbacks must not contact Auth'); };
  const cookies = new Map([[accountLinks.AUTH_RETURN_COOKIE, encodeURIComponent('/markets/durham-foodie-fare')]]);
  for (const query of ['', '?error=access_denied&error_description=private-detail', '?code=x&sb_flow_id=invalid', `?code=${'x'.repeat(2049)}`]) {
    const response = await callback(query, cookies);
    const destination = new URL(response.headers.get('location'));
    assert.equal(destination.origin, origin);
    assert.equal(destination.pathname, '/login');
    assert.equal(destination.searchParams.get('auth_error'), query.includes('access_denied') ? 'cancelled' : 'failed');
    assert.equal(destination.searchParams.get('next'), '/markets/durham-foodie-fare');
    assert(!destination.href.includes('private-detail'));
    assertPrivate(response);
  }
});

test('a missing or rejected verifier cannot sign a visitor in or expose provider details', async () => {
  let exchanges = 0;
  tokenFetch(() => exchanges++, { fail: true });
  const missing = await callback('?code=fixture-code');
  assert.equal(exchanges, 0);
  assert.equal(missing.headers.get('location'), `${origin}/login?auth_error=failed`);
  const { cookies } = await startFlow();
  const rejected = await callback('?code=fixture-code', cookies);
  assert.equal(exchanges, 1);
  assert.equal(rejected.headers.get('location'), `${origin}/login?auth_error=failed`);
  assert(!rejected.cookies.getAll().some(cookie => cookie.name === 'sb-fixture-project-auth-token' && cookie.value));
  assertPrivate(rejected);
});

test('redirects reject external URLs, encoded host tricks, auth loops and malformed cookies', async () => {
  for (const path of ['//evil.example', '/\\evil.example', '/auth/callback', '/login?next=/auth/callback', 'https://evil.example', '/%2f%2fevil.example']) {
    assert.equal(accountLinks.authReturnPath(path, encodeURIComponent(path)), '/login');
    assert.equal(new URL(accountLinks.authFailurePath(path), origin).searchParams.has('next'), false);
  }
  assert.equal(accountLinks.authReturnPath(null, '%E0%A4%A'), '/login');
  assert.equal(accountLinks.authReturnPath('/verify', encodeURIComponent('/opportunities')), '/verify');
  assert.equal(accountLinks.authFailureMessage('raw-provider-detail'), '');
  assert.match(accountLinks.authReturnCookie('//evil.example', true), /^btb_auth_return_to=%2Flogin;.*SameSite=Lax; Secure$/);
  assert(!accountLinks.authReturnCookie('/verify', false).includes('Secure'));
});

test('Google is offered only when enabled; settings failures preserve email login', async () => {
  for (const [settings, enabled] of [[{ external: { google: true } }, true], [{ external: { google: false } }, false], [{ external: { google: 'true' } }, false], [{}, false], [null, false]]) {
    globalThis.fetch = async (url, options) => {
      assert.equal(url, `${authUrl}/auth/v1/settings`);
      assert.equal(options.headers.apikey, 'fixture-public-key');
      assert.equal(options.cache, 'no-store');
      return Response.json(settings);
    };
    assert.equal(await googleSignInEnabled(), enabled);
  }
  globalThis.fetch = async () => new Response('Unavailable', { status: 503 });
  assert.equal(await googleSignInEnabled(), false);
  globalThis.fetch = async () => { throw new Error('Network failure'); };
  assert.equal(await googleSignInEnabled(), false);
});
