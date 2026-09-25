import type {APIRequestContext} from '@playwright/test';

import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

const TOKEN_EXCHANGE_GRANT_TYPE =
  'urn:ietf:params:oauth:grant-type:token-exchange';
const JWT_TOKEN_TYPE = 'urn:ietf:params:oauth:token-type:jwt';
const ACCESS_TOKEN_TYPE = 'urn:ietf:params:oauth:token-type:access_token';

type KeycloakConfig = {
  tokenEndpoint: string;
  clientId: string;
};

type KeycloakTokenClaims = {
  iss: string;
  sub: string;
};

function getKeycloakConfig(quayConfig: {
  config: Record<string, unknown>;
}): KeycloakConfig | null {
  for (const value of Object.values(quayConfig.config)) {
    if (
      !value ||
      typeof value !== 'object' ||
      !('OIDC_SERVER' in value) ||
      !('CLIENT_ID' in value)
    ) {
      continue;
    }

    const loginConfig = value as Record<string, string>;
    let oidcServer = loginConfig.OIDC_SERVER;
    // The browser test process reaches Keycloak through the host port, while
    // Quay itself uses host.containers.internal from inside its container.
    oidcServer = oidcServer.replace('host.containers.internal', 'localhost');
    if (!oidcServer.endsWith('/')) oidcServer += '/';

    return {
      tokenEndpoint: `${oidcServer}protocol/openid-connect/token`,
      clientId: loginConfig.CLIENT_ID,
    };
  }

  return null;
}

async function getKeycloakAccessToken(
  request: APIRequestContext,
  keycloak: KeycloakConfig,
): Promise<string> {
  const response = await request.post(keycloak.tokenEndpoint, {
    form: {
      grant_type: 'password',
      client_id: keycloak.clientId,
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
  return (await response.json()).access_token as string;
}

function decodeJwtClaims(token: string): KeycloakTokenClaims {
  return JSON.parse(
    Buffer.from(token.split('.')[1], 'base64url').toString('utf-8'),
  ) as KeycloakTokenClaims;
}

test.describe(
  'Robot Federation Token Exchange',
  {tag: ['@api', '@auth:OIDC', '@superuser', '@PROJQUAY-11090']},
  () => {
    test('exchanges a Keycloak token through STS and the legacy endpoint', async ({
      request,
      quayConfig,
      superuserApi,
      adminClient,
    }) => {
      const keycloak = getKeycloakConfig(quayConfig);
      test.skip(!keycloak, 'No Keycloak OIDC login configuration found');
      if (!keycloak) return;

      const subjectToken = await getKeycloakAccessToken(request, keycloak);
      const claims = decodeJwtClaims(subjectToken);
      expect(claims.iss).toBeTruthy();
      expect(claims.sub).toBeTruthy();

      const organization = await superuserApi.organization('federation');
      const robot = await superuserApi.robot(organization.name, 'sts');
      const federationResponse = await adminClient.post(
        `/api/v1/organization/${organization.name}/robots/${robot.shortname}/federation`,
        [
          {
            issuer: claims.iss,
            subject: claims.sub,
            audiences: [keycloak.clientId],
            api_scopes: 'user:read',
          },
        ],
      );
      expect(federationResponse.status()).toBe(200);

      const stsResponse = await request.post(`${API_URL}/sts/token`, {
        form: {
          grant_type: TOKEN_EXCHANGE_GRANT_TYPE,
          subject_token: subjectToken,
          subject_token_type: JWT_TOKEN_TYPE,
          resource: `urn:quay:robot:${robot.fullName}`,
          scope: 'user:read',
        },
        timeout: 10_000,
      });
      expect(stsResponse.status()).toBe(200);
      const stsBody = await stsResponse.json();
      expect(stsBody.issued_token_type).toBe(ACCESS_TOKEN_TYPE);
      expect(stsBody.token_type).toBe('Bearer');
      expect(stsBody.scope).toBe('user:read');
      expect(stsBody.access_token).toBeTruthy();

      const legacyResponse = await request.get(
        `${API_URL}/oauth2/federation/robot/token?scope=user%3Aread`,
        {
          headers: {
            Authorization: `Basic ${Buffer.from(
              `${robot.fullName}:${subjectToken}`,
            ).toString('base64')}`,
          },
          timeout: 10_000,
        },
      );
      expect(legacyResponse.status()).toBe(200);
      const legacyBody = await legacyResponse.json();
      expect(legacyBody.token).toBeTruthy();

      for (const token of [stsBody.access_token, legacyBody.token]) {
        const userResponse = await request.get(`${API_URL}/api/v1/user/`, {
          headers: {Authorization: `Bearer ${token}`},
          timeout: 10_000,
        });
        expect(userResponse.status()).toBe(200);
        expect((await userResponse.json()).username).toBe(robot.fullName);
      }
    });
  },
);
