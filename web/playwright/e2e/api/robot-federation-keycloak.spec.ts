/**
 * Robot federation against the local Keycloak external OIDC issuer.
 *
 * These tests configure bindings with claims from real Keycloak access tokens,
 * then exchange those tokens for short-lived Quay robot JWTs.
 */

import type {APIRequestContext} from '@playwright/test';
import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

const KEYCLOAK_TOKEN_ENDPOINT =
  'http://localhost:8081/realms/quay/protocol/openid-connect/token';
const TOKEN_EXCHANGE_GRANT_TYPE =
  'urn:ietf:params:oauth:grant-type:token-exchange';
const JWT_TOKEN_TYPE = 'urn:ietf:params:oauth:token-type:jwt';

interface KeycloakTokenResponse {
  access_token: string;
}

interface FederationBinding {
  issuer: string;
  subject: string;
  audiences: string[];
  api_scopes: string;
  id?: string;
  version?: number;
}

function decodeJwtPayload(token: string): Record<string, unknown> {
  const payload = token.split('.')[1];
  return JSON.parse(Buffer.from(payload, 'base64url').toString('utf-8'));
}

function tokenAudiences(claims: Record<string, unknown>): string[] {
  const audience = claims.aud;
  if (typeof audience === 'string') {
    return [audience];
  }
  return Array.isArray(audience)
    ? audience.filter((value): value is string => typeof value === 'string')
    : [];
}

async function getKeycloakAccessToken(
  request: APIRequestContext,
): Promise<string> {
  const response = await request.post(KEYCLOAK_TOKEN_ENDPOINT, {
    form: {
      grant_type: 'password',
      client_id: 'quay-ui',
      username: 'testuser_oidc',
      password: 'password',
      scope: 'openid profile email',
    },
    timeout: 10_000,
  });

  expect(
    response.ok(),
    `Keycloak token request failed: ${response.status()}`,
  ).toBe(true);
  return ((await response.json()) as KeycloakTokenResponse).access_token;
}

async function exchangeFederatedToken(
  request: APIRequestContext,
  robotName: string,
  externalToken: string,
  requestedScope: string,
) {
  return request.post(`${API_URL}/sts/token`, {
    form: {
      grant_type: TOKEN_EXCHANGE_GRANT_TYPE,
      subject_token: externalToken,
      subject_token_type: JWT_TOKEN_TYPE,
      resource: `urn:quay:robot:${robotName}`,
      scope: requestedScope,
    },
    timeout: 10_000,
  });
}

test.describe(
  'Robot federation with Keycloak',
  {
    tag: [
      '@api',
      '@auth:OIDC',
      '@config:OIDC',
      '@PROJQUAY-11090',
      '@feature:ROBOT_API_TOKENS',
      '@feature:ROBOT_API_TOKEN_EXCHANGE',
    ],
  },
  () => {
    test('exchanges a Keycloak token matching the configured binding and scope', async ({
      api,
      authenticatedRequest,
      csrfToken,
      request,
      quayConfig,
    }) => {
      test.skip(
        quayConfig.config.AUTHENTICATION_TYPE !== 'OIDC',
        'Requires Keycloak OIDC authentication',
      );

      const externalToken = await getKeycloakAccessToken(request);
      const externalClaims = decodeJwtPayload(externalToken);
      const issuer = externalClaims.iss;
      const subject = externalClaims.sub;
      const audiences = tokenAudiences(externalClaims);
      expect(typeof issuer).toBe('string');
      expect(typeof subject).toBe('string');
      expect(audiences).toContain('quay-ui');

      const org = await api.organization('keycloak-federation');
      const robot = await api.robot(org.name, 'bound-robot');
      const binding: FederationBinding = {
        issuer: issuer as string,
        subject: subject as string,
        audiences: ['quay-ui'],
        api_scopes: 'repo:read',
      };
      const configureResponse = await authenticatedRequest.post(
        `${API_URL}/api/v1/organization/${org.name}/robots/${robot.shortname}/federation`,
        {
          headers: {'X-CSRF-Token': csrfToken},
          data: [binding],
        },
      );
      expect(configureResponse.status()).toBe(200);
      const [savedBinding] =
        (await configureResponse.json()) as FederationBinding[];

      const exchangeResponse = await exchangeFederatedToken(
        request,
        robot.fullName,
        externalToken,
        'repo:read',
      );
      expect(exchangeResponse.status()).toBe(200);
      const {access_token: token} = (await exchangeResponse.json()) as {
        access_token: string;
      };
      const robotClaims = decodeJwtPayload(token);
      expect(robotClaims.api_scopes).toBe('repo:read');
      expect(robotClaims.federation_binding_id).toBe(savedBinding.id);
      expect(robotClaims.federation_binding_version).toBe(savedBinding.version);
    });

    test('rejects a requested scope outside the Keycloak binding', async ({
      api,
      authenticatedRequest,
      csrfToken,
      request,
      quayConfig,
    }) => {
      test.skip(
        quayConfig.config.AUTHENTICATION_TYPE !== 'OIDC',
        'Requires Keycloak OIDC authentication',
      );

      const externalToken = await getKeycloakAccessToken(request);
      const externalClaims = decodeJwtPayload(externalToken);
      const org = await api.organization('keycloak-scope');
      const robot = await api.robot(org.name, 'scope-robot');
      const configureResponse = await authenticatedRequest.post(
        `${API_URL}/api/v1/organization/${org.name}/robots/${robot.shortname}/federation`,
        {
          headers: {'X-CSRF-Token': csrfToken},
          data: [
            {
              issuer: externalClaims.iss,
              subject: externalClaims.sub,
              audiences: ['quay-ui'],
              api_scopes: 'repo:read',
            },
          ],
        },
      );
      expect(configureResponse.status()).toBe(200);

      const exchangeResponse = await exchangeFederatedToken(
        request,
        robot.fullName,
        externalToken,
        'repo:write',
      );
      expect(exchangeResponse.status()).toBe(400);
      await expect(exchangeResponse.json()).resolves.toEqual({
        error: 'Requested scope is not allowed for this federation binding',
      });
    });

    test('rejects a Keycloak token whose audience is not in the binding', async ({
      api,
      authenticatedRequest,
      csrfToken,
      request,
      quayConfig,
    }) => {
      test.skip(
        quayConfig.config.AUTHENTICATION_TYPE !== 'OIDC',
        'Requires Keycloak OIDC authentication',
      );

      const externalToken = await getKeycloakAccessToken(request);
      const externalClaims = decodeJwtPayload(externalToken);
      const org = await api.organization('keycloak-audience');
      const robot = await api.robot(org.name, 'audience-robot');
      const configureResponse = await authenticatedRequest.post(
        `${API_URL}/api/v1/organization/${org.name}/robots/${robot.shortname}/federation`,
        {
          headers: {'X-CSRF-Token': csrfToken},
          data: [
            {
              issuer: externalClaims.iss,
              subject: externalClaims.sub,
              audiences: ['not-quay-ui'],
              api_scopes: 'repo:read',
            },
          ],
        },
      );
      expect(configureResponse.status()).toBe(200);

      const exchangeResponse = await exchangeFederatedToken(
        request,
        robot.fullName,
        externalToken,
        'repo:read',
      );
      expect(exchangeResponse.status()).toBe(400);
      await expect(exchangeResponse.json()).resolves.toEqual({
        error: 'invalid_grant',
      });
    });
  },
);
