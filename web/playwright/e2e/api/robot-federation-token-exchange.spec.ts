import type {APIRequestContext} from '@playwright/test';

import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

const TOKEN_EXCHANGE_GRANT_TYPE =
  'urn:ietf:params:oauth:grant-type:token-exchange';
const JWT_TOKEN_TYPE = 'urn:ietf:params:oauth:token-type:jwt';
const ACCESS_TOKEN_TYPE = 'urn:ietf:params:oauth:token-type:access_token';
// Playwright runs on the host, where localhost reaches the published port.
// Keycloak is configured to issue the container-reachable host alias as `iss`.
const KEYCLOAK_TOKEN_ENDPOINT =
  'http://localhost:8081/realms/quay/protocol/openid-connect/token';
const KEYCLOAK_CLIENT_ID = 'quay-ui';

type KeycloakTokenClaims = {
  iss: string;
  sub: string;
};

async function getKeycloakAccessToken(
  request: APIRequestContext,
): Promise<string> {
  const response = await request.post(KEYCLOAK_TOKEN_ENDPOINT, {
    form: {
      grant_type: 'password',
      client_id: KEYCLOAK_CLIENT_ID,
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
      superuserApi,
    }) => {
      const subjectToken = await getKeycloakAccessToken(request);
      const claims = decodeJwtClaims(subjectToken);
      expect(claims.iss).toBeTruthy();
      expect(claims.sub).toBeTruthy();

      const organization = await superuserApi.organization('federation');
      const robot = await superuserApi.robot(organization.name, 'sts');
      await superuserApi.raw.createRobotFederation(
        organization.name,
        robot.shortname,
        [
          {
            issuer: claims.iss,
            subject: claims.sub,
            audiences: [KEYCLOAK_CLIENT_ID],
            api_scopes: 'user:read',
          },
        ],
      );

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
