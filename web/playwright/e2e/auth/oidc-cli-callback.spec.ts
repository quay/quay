/**
 * OIDC CLI-credential flow: /oauth2/<service>/callback/cli.
 *
 * No UI starts the "cli" kind, so each test starts it through
 * POST /api/v1/externallogin/<service> from the signed-in user's context.
 */

import {APIRequestContext} from '@playwright/test';
import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {requestCsrfToken} from '../../utils/api/csrf';
import {API_URL, BASE_URL} from '../../utils/config';

async function startCliLogin(
  request: APIRequestContext,
  serviceId: string,
): Promise<URL> {
  const csrfToken = await requestCsrfToken(request, BASE_URL);
  const response = await request.post(
    `${BASE_URL}/api/v1/externallogin/${serviceId}`,
    {data: {kind: 'cli'}, headers: {'X-CSRF-Token': csrfToken}},
  );
  expect(response.status()).toBe(200);
  return new URL((await response.json()).auth_url);
}

function decodeJwtPayload(token: string): Record<string, unknown> {
  const parts = token.split('.');
  expect(parts).toHaveLength(3);
  return JSON.parse(Buffer.from(parts[1], 'base64url').toString('utf-8'));
}

test.describe('OIDC CLI token callback', {tag: ['@auth', '@auth:OIDC']}, () => {
  test.beforeEach(({quayConfig}) => {
    test.skip(
      quayConfig?.config?.AUTHENTICATION_TYPE !== 'OIDC' ||
        !quayConfig?.external_login?.length,
      'Requires AUTHENTICATION_TYPE: OIDC with an external login provider',
    );
  });

  test('returns an ID token for the signed-in user', async ({
    authenticatedPage: page,
    quayConfig,
  }) => {
    const provider = quayConfig.external_login![0];
    const request = page.context().request;
    const authUrl = await startCliLogin(request, provider.id);
    const callbackPath = `/oauth2/${provider.id}/callback/cli`;
    expect(new URL(authUrl.searchParams.get('redirect_uri')!).pathname).toBe(
      callbackPath,
    );

    // The context already has a Keycloak SSO session, so prompt=login
    // shows Keycloak's password-only re-authentication form.
    authUrl.searchParams.set('prompt', 'login');
    await page.goto(authUrl.toString());
    await page.fill('#password', TEST_USERS.user.password);
    const callback = page.waitForResponse(
      (r) => new URL(r.url()).pathname === callbackPath,
    );
    await page.click('#kc-login');
    const response = await callback;

    expect(response.status()).toBe(302);
    const location = new URL(response.headers()['location']);
    expect(location.pathname).toBe(`/user/${TEST_USERS.user.username}/`);
    expect(location.searchParams.get('tab')).toBe('settings');

    const claims = decodeJwtPayload(location.searchParams.get('idtoken')!);
    // The authorization endpoint is <issuer>/protocol/openid-connect/auth.
    expect(claims.iss).toBe(
      authUrl.origin +
        authUrl.pathname.replace(/\/protocol\/openid-connect\/auth$/, ''),
    );
    expect(claims.aud).toBe(authUrl.searchParams.get('client_id'));
    expect(claims.preferred_username).toBe(TEST_USERS.user.username);

    const user = await (await request.get(`${BASE_URL}/api/v1/user/`)).json();
    const login = user.logins.find(
      (l: {service: string}) => l.service === provider.id,
    );
    expect(claims.sub).toBe(login.service_identifier);
  });

  test('rejects the callback without a session', async ({
    request,
    quayConfig,
  }) => {
    const provider = quayConfig.external_login![0];
    const response = await request.get(
      `${API_URL}/oauth2/${provider.id}/callback/cli?code=x&state=x`,
      {maxRedirects: 0},
    );
    expect(response.status()).toBe(401);
  });

  test('rejects a state that does not match the session', async ({
    authenticatedPage: page,
    quayConfig,
  }) => {
    const provider = quayConfig.external_login![0];
    const request = page.context().request;
    const authUrl = await startCliLogin(request, provider.id);
    const callbackUrl = new URL(authUrl.searchParams.get('redirect_uri')!);
    callbackUrl.searchParams.set('code', 'x');
    callbackUrl.searchParams.set('state', 'not-the-session-token');
    const response = await request.get(callbackUrl.toString(), {
      maxRedirects: 0,
    });
    expect(response.status()).toBe(403);
  });

  test('sends a provider error to the OAuth error page', async ({
    authenticatedPage: page,
    quayConfig,
  }) => {
    const provider = quayConfig.external_login![0];
    const request = page.context().request;
    const authUrl = await startCliLogin(request, provider.id);
    const callbackUrl = new URL(authUrl.searchParams.get('redirect_uri')!);
    callbackUrl.searchParams.set('state', authUrl.searchParams.get('state')!);
    callbackUrl.searchParams.set('error', 'access_denied');
    const response = await request.get(callbackUrl.toString(), {
      maxRedirects: 0,
    });

    expect(response.status()).toBe(302);
    const location = new URL(response.headers()['location']);
    expect(location.pathname).toBe('/oauth-error');
    expect(location.searchParams.get('error_description')).toBe(
      'access_denied',
    );
    expect(location.searchParams.get('provider')).toBe(provider.title);
    expect(location.searchParams.get('authenticated')).toBe('true');
    expect(location.searchParams.get('username')).toBe(
      TEST_USERS.user.username,
    );
  });
});
