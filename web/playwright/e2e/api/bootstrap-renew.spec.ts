/**
 * Bootstrap token renewal API tests.
 *
 * Successful token rotation is covered by pytest because it needs access to the
 * generated bootstrap token and server-side token storage. This E2E check
 * verifies the externally observable routing and bearer-auth behavior.
 */

import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

const BOOTSTRAP_RENEW_PATH = '/api/v1/bootstrap/renew';

function isProgrammaticBootstrapEnabled(features: unknown): boolean {
  const featureMap = features as Record<string, boolean | undefined>;
  return featureMap.PROGRAMMATIC_BOOTSTRAP === true;
}

// Execute these tests whether PROGRAMMATIC_BOOTSTRAP is enabled or disabled.
test.describe(
  'Bootstrap token renewal method handling',
  {tag: ['@api', '@PROJQUAY-12443']},
  () => {
    for (const method of ['GET', 'HEAD']) {
      for (const suffix of ['', '/']) {
        test(`${method} ${BOOTSTRAP_RENEW_PATH}${suffix} rejects reads without redirecting`, async ({
          request,
        }) => {
          const response = await request.fetch(
            `${API_URL}${BOOTSTRAP_RENEW_PATH}${suffix}`,
            {method, maxRedirects: 0, timeout: 10_000},
          );

          expect(response.status()).toBe(405);
          expect(response.headers().location).toBeUndefined();
          expect(response.headers().allow).toBe('POST, OPTIONS');
        });
      }
    }
  },
);

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
      request,
    }) => {
      const response = await request.post(
        `${API_URL}${BOOTSTRAP_RENEW_PATH}/`,
        {
          maxRedirects: 0,
          timeout: 10_000,
        },
      );

      expect(response.status()).toBe(307);
      expect(response.headers().location).toBe(BOOTSTRAP_RENEW_PATH);
    });

    for (const suffix of ['', '/']) {
      test(`rejects invalid bearer token at renewal${suffix} without accepting CSRF fallback`, async ({
        request,
        quayConfig,
      }) => {
        const response = await request.post(
          `${API_URL}${BOOTSTRAP_RENEW_PATH}${suffix}`,
          {
            headers: {
              Authorization: 'Bearer definitely-invalid-bootstrap-token',
            },
            timeout: 10_000,
            maxRedirects: 1,
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
      });
    }
  },
);
