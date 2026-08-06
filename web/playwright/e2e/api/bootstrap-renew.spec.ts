/**
 * Bootstrap token renewal API tests.
 *
 * Successful token rotation is covered by pytest because it needs access to the
 * generated bootstrap token and server-side token storage. This E2E check
 * verifies the externally observable bearer-auth behavior for the endpoint.
 */

import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

const BOOTSTRAP_RENEW_PATH = '/api/v1/bootstrap/renew';

function isProgrammaticBootstrapEnabled(features: unknown): boolean {
  const featureMap = features as Record<string, boolean | undefined>;
  return featureMap.PROGRAMMATIC_BOOTSTRAP === true;
}

test.describe(
  'Bootstrap token renewal API',
  {
    tag: [
      '@api',
      '@auth:Database',
      '@feature:PROGRAMMATIC_BOOTSTRAP',
      '@PROJQUAY-12443',
    ],
  },
  () => {
    test('redirects trailing slash to canonical renewal endpoint', async ({
      playwright,
    }) => {
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });

      try {
        const response = await request.post(
          `${API_URL}${BOOTSTRAP_RENEW_PATH}/`,
          {
            maxRedirects: 0,
            timeout: 10_000,
          },
        );

        expect(response.status()).toBe(307);
        expect(response.headers().location).toBe(BOOTSTRAP_RENEW_PATH);
      } finally {
        await request.dispose();
      }
    });

    test('rejects invalid bearer token without accepting CSRF fallback', async ({
      playwright,
      quayConfig,
    }) => {
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });

      try {
        const response = await request.post(
          `${API_URL}${BOOTSTRAP_RENEW_PATH}`,
          {
            headers: {
              Authorization: 'Bearer definitely-invalid-bootstrap-token',
            },
            timeout: 10_000,
          },
        );

        if (!isProgrammaticBootstrapEnabled(quayConfig.features)) {
          // The API resource is not registered, but Quay's GET-only web
          // catch-all route still matches the path and rejects POST.
          expect(response.status()).toBe(405);
          return;
        }

        expect(response.status()).toBe(401);
        const body = await response.json();
        expect(body.error_type).toBe('invalid_token');
      } finally {
        await request.dispose();
      }
    });
  },
);
