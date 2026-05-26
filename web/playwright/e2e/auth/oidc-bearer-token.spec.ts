/**
 * OIDC Bearer Token API Authentication Tests
 *
 * Verifies that access tokens obtained from an OIDC provider can be used
 * as Bearer tokens for Quay API calls. Covers both standard JWT tokens
 * (typ: JWT) and RFC 9068 tokens (typ: at+jwt).
 *
 * Regression test for PROJQUAY-11205: is_jwt() was rejecting at+jwt tokens,
 * misrouting them to internal OAuth lookup instead of SSO JWT validation.
 *
 * Requires OIDC auth with Keycloak and directAccessGrantsEnabled on the client.
 */

import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

/**
 * Extract the OIDC server URL and client ID from Quay config.
 * Returns null if no OIDC provider is configured.
 */
function getOidcConfig(quayConfig: {config: Record<string, unknown>}): {
  tokenEndpoint: string;
  clientId: string;
} | null {
  const config = quayConfig.config;
  for (const [key, value] of Object.entries(config)) {
    if (
      key.endsWith('_LOGIN_CONFIG') &&
      value &&
      typeof value === 'object' &&
      'OIDC_SERVER' in (value as Record<string, unknown>) &&
      'CLIENT_ID' in (value as Record<string, unknown>)
    ) {
      const loginConfig = value as Record<string, string>;
      let oidcServer = loginConfig.OIDC_SERVER;
      // Keycloak runs inside containers, but tests run on the host.
      // Replace container-internal hostnames with localhost.
      oidcServer = oidcServer.replace('host.containers.internal', 'localhost');
      if (!oidcServer.endsWith('/')) oidcServer += '/';
      return {
        tokenEndpoint: `${oidcServer}protocol/openid-connect/token`,
        clientId: loginConfig.CLIENT_ID,
      };
    }
  }
  return null;
}

/**
 * Decode a JWT's header without verification (base64url → JSON).
 */
function decodeJwtHeader(token: string): Record<string, string> {
  const headerB64 = token.split('.')[0];
  const json = Buffer.from(headerB64, 'base64url').toString('utf-8');
  return JSON.parse(json);
}

test.describe(
  'OIDC Bearer Token Auth',
  {tag: ['@api', '@auth:OIDC', '@PROJQUAY-11205']},
  () => {
    test('access_token from Keycloak ROPC grant authenticates Quay API', async ({
      playwright,
      quayConfig,
    }) => {
      const oidc = getOidcConfig(quayConfig);
      test.skip(!oidc, 'No OIDC login config with OIDC_SERVER found');
      if (!oidc) return;

      // Obtain an access_token via Resource Owner Password Credentials grant
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const tokenResponse = await request.post(oidc.tokenEndpoint, {
          form: {
            grant_type: 'password',
            client_id: oidc.clientId,
            username: 'testuser_oidc',
            password: 'password',
            scope: 'openid profile email',
          },
          timeout: 10_000,
        });

        expect(
          tokenResponse.ok(),
          `Keycloak token request failed: ${tokenResponse.status()}`,
        ).toBe(true);

        const tokenBody = await tokenResponse.json();
        const accessToken: string = tokenBody.access_token;
        expect(accessToken).toBeTruthy();

        // Log the token typ for diagnostic purposes
        const header = decodeJwtHeader(accessToken);
        const typ = header.typ || '(none)';
        // eslint-disable-next-line no-console
        console.log(`Access token typ: "${typ}"`);

        // Use the access_token as a Bearer token for a Quay API call
        const apiResponse = await request.get(`${API_URL}/api/v1/user/`, {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          timeout: 10_000,
        });

        // The fix in PROJQUAY-11205 ensures is_jwt() accepts both "jwt" and "at+jwt",
        // routing the token to SSO JWT validation instead of internal OAuth lookup.
        expect(apiResponse.status()).toBe(200);

        const userBody = await apiResponse.json();
        expect(userBody.username).toBeTruthy();
      } finally {
        await request.dispose();
      }
    });

    test('id_token from Keycloak ROPC grant authenticates Quay API', async ({
      playwright,
      quayConfig,
    }) => {
      const oidc = getOidcConfig(quayConfig);
      test.skip(!oidc, 'No OIDC login config with OIDC_SERVER found');
      if (!oidc) return;

      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const tokenResponse = await request.post(oidc.tokenEndpoint, {
          form: {
            grant_type: 'password',
            client_id: oidc.clientId,
            username: 'testuser_oidc',
            password: 'password',
            scope: 'openid profile email',
          },
          timeout: 10_000,
        });

        expect(
          tokenResponse.ok(),
          `Keycloak token request failed: ${tokenResponse.status()}`,
        ).toBe(true);

        const tokenBody = await tokenResponse.json();
        const idToken: string = tokenBody.id_token;
        expect(idToken).toBeTruthy();

        const header = decodeJwtHeader(idToken);
        expect(header.typ?.toLowerCase()).toBe('jwt');

        // id_token (typ: JWT) should also work as a Bearer token
        const apiResponse = await request.get(`${API_URL}/api/v1/user/`, {
          headers: {
            Authorization: `Bearer ${idToken}`,
          },
          timeout: 10_000,
        });

        expect(apiResponse.status()).toBe(200);

        const userBody = await apiResponse.json();
        expect(userBody.username).toBeTruthy();
      } finally {
        await request.dispose();
      }
    });

    test('invalid Bearer token is rejected', async ({
      playwright,
      quayConfig,
    }) => {
      const oidc = getOidcConfig(quayConfig);
      test.skip(!oidc, 'No OIDC login config with OIDC_SERVER found');
      if (!oidc) return;

      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const apiResponse = await request.get(`${API_URL}/api/v1/user/`, {
          headers: {
            Authorization: 'Bearer invalid-token-value',
          },
          timeout: 10_000,
        });

        // Should be rejected — not a valid JWT or OAuth token
        expect([401, 403]).toContain(apiResponse.status());
      } finally {
        await request.dispose();
      }
    });
  },
);
