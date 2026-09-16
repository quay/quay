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
  return request.get(
    `${API_URL}/oauth2/federation/robot/token?scope=${encodeURIComponent(requestedScope)}`,
    {
      headers: {
        Authorization: `Basic ${Buffer.from(`${robotName}:${externalToken}`).toString('base64')}`,
      },
      timeout: 10_000,
    },
  );
}

test.describe(
  'Robot federation with Keycloak',
  {tag: ['@api', '@auth:OIDC', '@config:OIDC', '@PROJQUAY-11090']},
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
      const {token} = (await exchangeResponse.json()) as {token: string};
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
        message: 'Token audience is not allowed for this robot',
      });
    });
  },
);
