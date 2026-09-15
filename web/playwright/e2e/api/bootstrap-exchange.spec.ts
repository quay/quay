/**
 * Kubernetes ServiceAccount workload-identity token exchange.
 *
 * The positive and wrong-audience cases require a real projected ServiceAccount
 * token. Provide those tokens from the cluster setup rather than minting or
 * mocking JWTs in Playwright:
 *
 *   WORKLOAD_IDENTITY_SUBJECT_TOKEN=<valid token>
 *   WORKLOAD_IDENTITY_WRONG_AUDIENCE_TOKEN=<token with another audience>
 *   WORKLOAD_IDENTITY_INVALID_SIGNATURE_TOKEN=<token signed by an unknown key>
 *   WORKLOAD_IDENTITY_UNAUTHORIZED_TOKEN=<valid token for an unmapped subject>
 *
 * These tests are intentionally skipped when the workload-identity feature is
 * not enabled or the cluster setup did not provide the relevant token.
 */

import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

const EXCHANGE_PATH = '/api/v1/bootstrap/exchange';
const TOKEN_EXCHANGE_GRANT = 'urn:ietf:params:oauth:grant-type:token-exchange';
const JWT_SUBJECT_TOKEN_TYPE = 'urn:ietf:params:oauth:token-type:jwt';

function exchangeForm(subjectToken: string, scope?: string) {
  return {
    grant_type: TOKEN_EXCHANGE_GRANT,
    subject_token_type: JWT_SUBJECT_TOKEN_TYPE,
    subject_token: subjectToken,
    ...(scope ? {scope} : {}),
  };
}

async function expectInvalidToken(response: {
  status: () => number;
  json: () => Promise<unknown>;
}) {
  expect(response.status()).toBe(401);
  const body = (await response.json()) as {error_type?: string; error?: string};
  expect(body.error_type ?? body.error).toBe('invalid_token');
}

test.describe(
  'Kubernetes ServiceAccount workload identity exchange API',
  {
    tag: [
      '@api',
      '@feature:KUBERNETES_SA_BOOTSTRAP',
      '@PROJQUAY-12484',
      '@PROJQUAY-12487',
    ],
  },
  () => {
    test('rejects a malformed subject token', async ({playwright}) => {
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const response = await request.post(`${API_URL}${EXCHANGE_PATH}`, {
          form: exchangeForm('not-a-jwt'),
        });
        await expectInvalidToken(response);
      } finally {
        await request.dispose();
      }
    });

    test('rejects a ServiceAccount token with the wrong audience', async ({
      playwright,
    }) => {
      const token = process.env.WORKLOAD_IDENTITY_WRONG_AUDIENCE_TOKEN;
      test.skip(!token, 'WORKLOAD_IDENTITY_WRONG_AUDIENCE_TOKEN is not set');

      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const response = await request.post(`${API_URL}${EXCHANGE_PATH}`, {
          form: exchangeForm(token!),
        });
        await expectInvalidToken(response);
      } finally {
        await request.dispose();
      }
    });

    test('rejects a token with an invalid signature', async ({playwright}) => {
      const token = process.env.WORKLOAD_IDENTITY_INVALID_SIGNATURE_TOKEN;
      test.skip(!token, 'WORKLOAD_IDENTITY_INVALID_SIGNATURE_TOKEN is not set');

      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const response = await request.post(`${API_URL}${EXCHANGE_PATH}`, {
          form: exchangeForm(token!),
        });
        await expectInvalidToken(response);
      } finally {
        await request.dispose();
      }
    });

    test('rejects a valid token for an unauthorized ServiceAccount', async ({
      playwright,
    }) => {
      const token = process.env.WORKLOAD_IDENTITY_UNAUTHORIZED_TOKEN;
      test.skip(!token, 'WORKLOAD_IDENTITY_UNAUTHORIZED_TOKEN is not set');

      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const response = await request.post(`${API_URL}${EXCHANGE_PATH}`, {
          form: exchangeForm(token!),
        });
        expect(response.status()).toBe(403);
        const body = (await response.json()) as {
          error_type?: string;
          error?: string;
        };
        expect(body.error_type ?? body.error).toBe('unauthorized');
      } finally {
        await request.dispose();
      }
    });

    test('exchanges a valid ServiceAccount token and uses the returned token', async ({
      playwright,
    }) => {
      const subjectToken = process.env.WORKLOAD_IDENTITY_SUBJECT_TOKEN;
      const configuredScope = process.env.WORKLOAD_IDENTITY_SCOPE;
      test.skip(
        !subjectToken || !configuredScope,
        'WORKLOAD_IDENTITY_SUBJECT_TOKEN and WORKLOAD_IDENTITY_SCOPE are required',
      );

      const requestedScope = `${configuredScope} ${configuredScope}`;
      const expectedScope = [...new Set(requestedScope.split(/\s+/))]
        .sort()
        .join(' ');
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const response = await request.post(`${API_URL}${EXCHANGE_PATH}`, {
          form: exchangeForm(subjectToken!, requestedScope),
        });
        expect(response.status()).toBe(200);
        const body = (await response.json()) as {
          access_token?: string;
          token_type?: string;
          expires_in?: number;
          scope?: string;
        };
        expect(body.access_token).toEqual(expect.any(String));
        expect(body.token_type).toBe('Bearer');
        expect(body.expires_in).toEqual(expect.any(Number));
        expect(body.scope).toBe(expectedScope);

        const managementResponse = await request.get(
          `${API_URL}${process.env.WORKLOAD_IDENTITY_MANAGEMENT_PATH ?? '/api/v1/user/'}`,
          {headers: {Authorization: `Bearer ${body.access_token}`}},
        );
        expect(managementResponse.status()).toBe(200);
      } finally {
        await request.dispose();
      }
    });

    test('rejects a request containing an unauthorized scope', async ({
      playwright,
    }) => {
      const subjectToken = process.env.WORKLOAD_IDENTITY_SUBJECT_TOKEN;
      const configuredScope = process.env.WORKLOAD_IDENTITY_SCOPE;
      test.skip(
        !subjectToken || !configuredScope,
        'WORKLOAD_IDENTITY_SUBJECT_TOKEN and WORKLOAD_IDENTITY_SCOPE are required',
      );

      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      try {
        const response = await request.post(`${API_URL}${EXCHANGE_PATH}`, {
          form: exchangeForm(subjectToken!, `${configuredScope} unknown:scope`),
        });
        expect(response.status()).toBe(403);
        const body = (await response.json()) as {
          access_token?: string;
          error_type?: string;
          error?: string;
        };
        expect(body.access_token).toBeUndefined();
        expect(body.error_type ?? body.error).toBe('unauthorized');
      } finally {
        await request.dispose();
      }
    });
  },
);
