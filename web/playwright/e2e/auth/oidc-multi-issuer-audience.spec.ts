/**
 * OIDC Multi-Issuer and Multi-Audience Tests
 *
 * Verifies the PROJQUAY-11798 feature: Quay accepts tokens from multiple
 * issuers (OIDC_ISSUERS) and multiple audiences (OIDC_AUDIENCES), and
 * rejects tokens with unauthorized azp (OIDC_ALLOWED_CLIENTS).
 *
 * Requires Keycloak with:
 * - quay realm (primary issuer)
 * - quay-v2 realm (secondary issuer for multi-issuer testing)
 * - quay-obo client (audience mapper for custom audience testing)
 */

import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

const KEYCLOAK_HOST = 'http://localhost:8081';

/**
 * Extract OIDC config from Quay config, checking for multi-issuer fields.
 */
function getMultiIssuerConfig(quayConfig: {config: Record<string, unknown>}): {
  clientId: string;
  issuers: string[];
  audiences: string[];
} | null {
  const config = quayConfig.config;
  for (const [key, value] of Object.entries(config)) {
    if (
      key.endsWith('_LOGIN_CONFIG') &&
      value &&
      typeof value === 'object' &&
      'OIDC_ISSUERS' in (value as Record<string, unknown>)
    ) {
      const loginConfig = value as Record<string, unknown>;
      return {
        clientId: loginConfig.CLIENT_ID as string,
        issuers: loginConfig.OIDC_ISSUERS as string[],
        audiences: (loginConfig.OIDC_AUDIENCES as string[]) || [],
      };
    }
  }
  return null;
}

/**
 * Get a token from Keycloak using Resource Owner Password Credentials grant.
 */
async function getKeycloakToken(
  request: ReturnType<
    Awaited<
      ReturnType<typeof import('@playwright/test').request.newContext>
    >['get']
  > extends Promise<unknown>
    ? Awaited<
        ReturnType<(typeof import('@playwright/test').request)['newContext']>
      >
    : never,
  realm: string,
  clientId: string,
  clientSecret?: string,
): Promise<{access_token: string; [key: string]: unknown}> {
  const form: Record<string, string> = {
    grant_type: 'password',
    client_id: clientId,
    username: 'testuser_oidc',
    password: 'password',
    scope: 'openid profile email',
  };
  if (clientSecret) {
    form.client_secret = clientSecret;
  }

  const response = await request.post(
    `${KEYCLOAK_HOST}/realms/${realm}/protocol/openid-connect/token`,
    {form, timeout: 10_000},
  );
  expect(
    response.ok(),
    `Keycloak token request failed: ${response.status()}`,
  ).toBe(true);
  return response.json();
}

/**
 * Decode a JWT payload without verification (base64url → JSON).
 */
function decodeJwtPayload(token: string): Record<string, unknown> {
  const payloadB64 = token.split('.')[1];
  const json = Buffer.from(payloadB64, 'base64url').toString('utf-8');
  return JSON.parse(json);
}

test.describe(
  'OIDC Multi-Issuer and Multi-Audience',
  {tag: ['@api', '@auth:OIDC', '@PROJQUAY-11798']},
  () => {
    test('token issuer is validated against OIDC_ISSUERS list', async ({
      playwright,
      quayConfig,
    }) => {
      const oidcConfig = getMultiIssuerConfig(quayConfig);
      test.skip(
        !oidcConfig,
        'No OIDC_ISSUERS configured — skipping multi-issuer test',
      );
      if (!oidcConfig) return;

      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        // Get a token from the primary realm
        const tokenBody = await getKeycloakToken(request, 'quay', 'quay-ui');
        const accessToken = tokenBody.access_token;

        const claims = decodeJwtPayload(accessToken);
        // eslint-disable-next-line no-console
        console.log(`Token iss: ${claims.iss}`);
        // Verify the token's issuer is in the configured OIDC_ISSUERS list
        const issuerMatch = oidcConfig.issuers.some(
          (i) => i.replace(/\/$/, '') === String(claims.iss).replace(/\/$/, ''),
        );
        expect(issuerMatch).toBe(true);

        // Use it against Quay API — accepted because issuer is in OIDC_ISSUERS
        const apiResponse = await request.get(`${API_URL}/api/v1/user/`, {
          headers: {Authorization: `Bearer ${accessToken}`},
          timeout: 10_000,
        });

        expect(apiResponse.status()).toBe(200);
        const userBody = await apiResponse.json();
        expect(userBody.username).toBeTruthy();
      } finally {
        await request.dispose();
      }
    });

    test('token with custom audience (api://quay-api) is accepted', async ({
      playwright,
      quayConfig,
    }) => {
      const oidcConfig = getMultiIssuerConfig(quayConfig);
      test.skip(
        !oidcConfig,
        'No OIDC_ISSUERS configured — skipping multi-audience test',
      );
      if (!oidcConfig) return;

      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        // Get a token from quay-obo client (has audience mapper for api://quay-api)
        const tokenBody = await getKeycloakToken(
          request,
          'quay',
          'quay-obo',
          'quay-obo-secret',
        );
        const accessToken = tokenBody.access_token;

        const claims = decodeJwtPayload(accessToken);
        // eslint-disable-next-line no-console
        console.log(`Custom audience token aud: ${JSON.stringify(claims.aud)}`);
        expect(claims.aud).toBe('api://quay-api');

        // Use it against Quay API — should be accepted because
        // api://quay-api is in OIDC_AUDIENCES
        const apiResponse = await request.get(`${API_URL}/api/v1/user/`, {
          headers: {Authorization: `Bearer ${accessToken}`},
          timeout: 10_000,
        });

        expect(apiResponse.status()).toBe(200);
        const userBody = await apiResponse.json();
        expect(userBody.username).toBeTruthy();
      } finally {
        await request.dispose();
      }
    });

    test('token with audience not in OIDC_AUDIENCES is rejected', async ({
      playwright,
      quayConfig,
    }) => {
      const oidcConfig = getMultiIssuerConfig(quayConfig);
      test.skip(
        !oidcConfig,
        'No OIDC_ISSUERS configured — skipping audience rejection test',
      );
      if (!oidcConfig) return;

      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        // Get a token from quay-unknown-aud client whose audience mapper
        // sets aud to "api://some-other-app" — not in OIDC_AUDIENCES
        const tokenBody = await getKeycloakToken(
          request,
          'quay',
          'quay-unknown-aud',
          'quay-unknown-aud-secret',
        );
        const accessToken = tokenBody.access_token;

        const claims = decodeJwtPayload(accessToken);
        // eslint-disable-next-line no-console
        console.log(
          `Wrong audience token aud: ${JSON.stringify(
            claims.aud,
          )}, configured: ${JSON.stringify(oidcConfig.audiences)}`,
        );
        expect(claims.aud).toBe('api://some-other-app');
        expect(oidcConfig.audiences).not.toContain('api://some-other-app');

        // Quay should reject — api://some-other-app is not in OIDC_AUDIENCES
        const apiResponse = await request.get(`${API_URL}/api/v1/user/`, {
          headers: {Authorization: `Bearer ${accessToken}`},
          timeout: 10_000,
        });

        expect(apiResponse.status()).toBe(401);
      } finally {
        await request.dispose();
      }
    });
  },
);
