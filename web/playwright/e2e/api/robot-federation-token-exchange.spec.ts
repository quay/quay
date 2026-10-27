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
  api_scopes?: string;
  federation_binding_id?: string;
  federation_binding_version?: number;
};

type FederationBinding = {
  issuer: string;
  subject: string;
  audiences: string[];
  api_scopes?: string;
  id: string;
  version: number;
};

async function getKeycloakAccessToken(
  request: APIRequestContext,
  username = 'testuser_oidc',
): Promise<string> {
  const response = await request.post(KEYCLOAK_TOKEN_ENDPOINT, {
    form: {
      grant_type: 'password',
      client_id: KEYCLOAK_CLIENT_ID,
      username,
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

async function exchangeSubjectToken(
  request: APIRequestContext,
  robotName: string,
  subjectToken: string,
  scope = 'user:read',
) {
  return request.post(`${API_URL}/sts/token`, {
    form: {
      grant_type: TOKEN_EXCHANGE_GRANT_TYPE,
      subject_token: subjectToken,
      subject_token_type: JWT_TOKEN_TYPE,
      resource: `urn:quay:robot:${robotName}`,
      scope,
    },
    timeout: 10_000,
  });
}

async function exchangeForAccessToken(
  request: APIRequestContext,
  robotName: string,
  subjectToken: string,
): Promise<string> {
  const response = await exchangeSubjectToken(request, robotName, subjectToken);
  expect(response.status()).toBe(200);
  return (await response.json()).access_token as string;
}

async function userEndpointStatus(
  request: APIRequestContext,
  accessToken: string,
): Promise<number> {
  const response = await request.get(`${API_URL}/api/v1/user/`, {
    headers: {Authorization: `Bearer ${accessToken}`},
    timeout: 10_000,
  });
  return response.status();
}

async function legacyFederationToken(
  request: APIRequestContext,
  robotName: string,
  subjectToken: string,
) {
  return request.get(`${API_URL}/oauth2/federation/robot/token`, {
    headers: {
      Authorization: `Basic ${Buffer.from(
        `${robotName}:${subjectToken}`,
      ).toString('base64')}`,
    },
    timeout: 10_000,
  });
}

test.describe(
  'Robot Federation Token Exchange',
  {
    tag: [
      '@api',
      '@auth:OIDC',
      '@superuser',
      '@PROJQUAY-11090',
      '@feature:ROBOT_API_TOKENS',
      '@feature:ROBOT_API_TOKEN_EXCHANGE',
    ],
  },
  () => {
    test('exchanges a Keycloak token through STS without expanding the legacy endpoint', async ({
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

      const userResponse = await request.get(`${API_URL}/api/v1/user/`, {
        headers: {Authorization: `Bearer ${stsBody.access_token}`},
        timeout: 10_000,
      });
      expect(userResponse.status()).toBe(200);
      expect((await userResponse.json()).username).toBe(robot.fullName);

      const legacyClaims = decodeJwtClaims(legacyBody.token);
      expect(legacyClaims.api_scopes).toBeUndefined();
    });

    test(
      'keeps two bindings independently revocable across the token exchange',
      {tag: ['@PROJQUAY-13549', '@PROJQUAY-13546']},
      async ({api, authenticatedRequest, csrfToken, request}) => {
        // Two Keycloak users give the robot two bindings with distinct subjects.
        const subjectTokenA = await getKeycloakAccessToken(
          request,
          'testuser_oidc',
        );
        const subjectTokenB = await getKeycloakAccessToken(
          request,
          'readonly_oidc',
        );
        const claimsA = decodeJwtClaims(subjectTokenA);
        const claimsB = decodeJwtClaims(subjectTokenB);
        expect(claimsA.sub).not.toBe(claimsB.sub);

        const organization = await api.organization('federation');
        const robot = await api.robot(organization.name, 'lifecycle');
        const federationUrl = `${API_URL}/api/v1/organization/${organization.name}/robots/${robot.shortname}/federation`;
        const bindingFor = (claims: KeycloakTokenClaims) => ({
          issuer: claims.iss,
          subject: claims.sub,
          audiences: [KEYCLOAK_CLIENT_ID],
          api_scopes: 'user:read',
        });

        const configureResponse = await authenticatedRequest.post(
          federationUrl,
          {
            headers: {'X-CSRF-Token': csrfToken},
            data: [bindingFor(claimsA), bindingFor(claimsB)],
            timeout: 10_000,
          },
        );
        expect(configureResponse.status()).toBe(200);
        const saved = (await configureResponse.json()) as FederationBinding[];
        expect(saved).toHaveLength(2);
        expect(saved[0].id).toBeTruthy();
        expect(saved[1].id).toBeTruthy();
        expect(saved[0].id).not.toBe(saved[1].id);
        expect(saved.map((binding) => binding.version)).toEqual([1, 1]);

        const accessTokenA = await exchangeForAccessToken(
          request,
          robot.fullName,
          subjectTokenA,
        );
        const accessTokenB = await exchangeForAccessToken(
          request,
          robot.fullName,
          subjectTokenB,
        );
        expect(decodeJwtClaims(accessTokenA).federation_binding_id).toBe(
          saved[0].id,
        );
        expect(decodeJwtClaims(accessTokenB).federation_binding_id).toBe(
          saved[1].id,
        );
        expect(await userEndpointStatus(request, accessTokenA)).toBe(200);
        expect(await userEndpointStatus(request, accessTokenB)).toBe(200);

        // Remove the first binding the way the UI does: post only the retained one, with its id.
        const retainResponse = await authenticatedRequest.post(federationUrl, {
          headers: {'X-CSRF-Token': csrfToken},
          data: [saved[1]],
          timeout: 10_000,
        });
        expect(retainResponse.status()).toBe(200);
        await expect(retainResponse.json()).resolves.toEqual([saved[1]]);
        const listResponse = await authenticatedRequest.get(federationUrl, {
          timeout: 10_000,
        });
        expect(listResponse.status()).toBe(200);
        await expect(listResponse.json()).resolves.toEqual([saved[1]]);

        // The removed binding's token is dead; the retained binding's token still works.
        expect(await userEndpointStatus(request, accessTokenA)).toBe(401);
        expect(await userEndpointStatus(request, accessTokenB)).toBe(200);

        // The removed subject can no longer exchange; the retained subject still can.
        const deniedExchange = await exchangeSubjectToken(
          request,
          robot.fullName,
          subjectTokenA,
        );
        expect(deniedExchange.status()).toBe(400);
        await expect(deniedExchange.json()).resolves.toEqual({
          error: 'invalid_grant',
        });
        const retainedExchange = await exchangeSubjectToken(
          request,
          robot.fullName,
          subjectTokenB,
        );
        expect(retainedExchange.status()).toBe(200);

        // The legacy endpoint keeps issuing registry-only tokens for the retained binding and
        // denies the removed subject with a controlled error rather than a server error.
        const legacyResponse = await legacyFederationToken(
          request,
          robot.fullName,
          subjectTokenB,
        );
        expect(legacyResponse.status()).toBe(200);
        const legacyClaims = decodeJwtClaims(
          (await legacyResponse.json()).token,
        );
        expect(legacyClaims.sub).toBe(robot.fullName);
        expect(legacyClaims.api_scopes).toBeUndefined();
        expect(legacyClaims.federation_binding_id).toBeUndefined();
        const deniedLegacy = await legacyFederationToken(
          request,
          robot.fullName,
          subjectTokenA,
        );
        expect(deniedLegacy.status()).toBe(400);
        await expect(deniedLegacy.json()).resolves.toEqual({
          message: 'Token does not match robot',
        });
      },
    );
  },
);
