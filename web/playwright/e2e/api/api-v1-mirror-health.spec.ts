/**
 * Mirror Health API Tests
 *
 * Tests the /api/v1/repository/mirror/health endpoint across three roles:
 *   - adminClient  : superuser (full access, global + namespace-scoped)
 *   - userClient   : normal user (namespace-scoped only)
 *   - readonlyClient : global readonly superuser (read-only global access)
 *   - anonClient   : unauthenticated (should get 401)
 *
 * Validates:
 *   - Authorization: superuser global, readonly superuser global,
 *     normal user namespace-scoped, anonymous rejection
 *   - Response structure: top-level fields, nested objects
 *   - HTTP status codes: 200 for healthy, 503 for unhealthy
 *   - Cache-Control header: no-store
 *   - Query parameters: namespace, detailed, limit, offset
 */

import {test, expect} from '../../fixtures';
import {RawApiClient} from '../../utils/api';
import {API_URL} from '../../utils/config';
import {TEST_USERS, TEST_USERS_OIDC} from '../../global-setup';

const HEALTH_URL = '/api/v1/repository/mirror/health';

test.describe(
  'Mirror Health API',
  {tag: ['@api', '@feature:REPO_MIRROR']},
  () => {
    let readonlyClient: RawApiClient;
    let anonClient: RawApiClient;
    let normalUsername: string;

    test.beforeAll(async ({playwright, cachedQuayConfig}) => {
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      anonClient = new RawApiClient(request, API_URL);

      const users =
        cachedQuayConfig?.config?.AUTHENTICATION_TYPE === 'OIDC'
          ? TEST_USERS_OIDC
          : TEST_USERS;
      normalUsername = users.user.username;

      // Build readonly superuser client
      const roRequest = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });
      readonlyClient = new RawApiClient(roRequest, API_URL);
      try {
        await readonlyClient.signIn(
          users.readonly.username,
          users.readonly.password,
        );
      } catch {
        // If readonly user not configured, tests using it will skip individually
        readonlyClient = null as unknown as RawApiClient;
      }
    });

    // ========================================================================
    // Section 1 -- Superuser access (global)
    // ========================================================================

    test.describe('Superuser global access', () => {
      test('superuser can GET mirror health globally', async ({
        adminClient,
      }) => {
        const r = await adminClient.get(HEALTH_URL);
        // 200 (healthy) or 503 (unhealthy) are both valid
        expect([200, 503]).toContain(r.status());

        const body = await r.json();
        expect(body).toHaveProperty('healthy');
        expect(body).toHaveProperty('workers');
        expect(body).toHaveProperty('repositories');
        expect(body).toHaveProperty('tags_pending');
        expect(body).toHaveProperty('last_check');
        expect(body).toHaveProperty('issues');
      });

      test('response has correct structure', async ({adminClient}) => {
        const r = await adminClient.get(HEALTH_URL);
        expect([200, 503]).toContain(r.status());

        const body = await r.json();

        // workers object
        expect(body.workers).toHaveProperty('active');
        expect(body.workers).toHaveProperty('configured');
        expect(body.workers).toHaveProperty('status');
        expect(['healthy', 'degraded']).toContain(body.workers.status);

        // repositories object
        expect(body.repositories).toHaveProperty('total');
        expect(body.repositories).toHaveProperty('syncing');
        expect(body.repositories).toHaveProperty('completed');
        expect(body.repositories).toHaveProperty('failed');
        expect(body.repositories).toHaveProperty('never_run');

        // Counts are non-negative integers
        expect(body.repositories.total).toBeGreaterThanOrEqual(0);
        expect(body.repositories.syncing).toBeGreaterThanOrEqual(0);
        expect(body.repositories.completed).toBeGreaterThanOrEqual(0);
        expect(body.repositories.failed).toBeGreaterThanOrEqual(0);
        expect(body.repositories.never_run).toBeGreaterThanOrEqual(0);

        // tags_pending is a number
        expect(typeof body.tags_pending).toBe('number');

        // last_check is an ISO timestamp ending in Z
        expect(body.last_check).toMatch(/Z$/);

        // issues is an array
        expect(Array.isArray(body.issues)).toBe(true);
      });

      test('Cache-Control header is no-store', async ({adminClient}) => {
        const r = await adminClient.get(HEALTH_URL);
        expect([200, 503]).toContain(r.status());

        const cacheControl = r.headers()['cache-control'] || '';
        expect(cacheControl).toContain('no-cache');
        expect(cacheControl).toContain('no-store');
      });
    });

    // ========================================================================
    // Section 2 -- Readonly superuser access (global)
    // ========================================================================

    test.describe('Readonly superuser global access', () => {
      test('readonly superuser can GET mirror health globally', async () => {
        test.skip(!readonlyClient, 'Readonly superuser not configured');

        const r = await readonlyClient.get(HEALTH_URL);
        expect([200, 503]).toContain(r.status());

        const body = await r.json();
        expect(body).toHaveProperty('healthy');
        expect(body).toHaveProperty('repositories');
      });
    });

    // ========================================================================
    // Section 3 -- Normal user access
    // ========================================================================

    test.describe('Normal user access', () => {
      test('normal user cannot GET mirror health globally', async ({
        userClient,
      }) => {
        const r = await userClient.get(HEALTH_URL);
        // Should be denied — 401 (Unauthorized) or 403 (Forbidden)
        expect([401, 403]).toContain(r.status());
      });

      test('normal user can GET mirror health for own namespace', async ({
        userClient,
      }) => {
        const r = await userClient.get(
          `${HEALTH_URL}?namespace=${normalUsername}`,
        );
        expect([200, 503]).toContain(r.status());

        const body = await r.json();
        expect(body).toHaveProperty('healthy');
      });

      test('normal user cannot GET mirror health for other namespace', async ({
        userClient,
        superuserApi,
      }) => {
        const org = await superuserApi.organization('mhealthtest');

        const r = await userClient.get(`${HEALTH_URL}?namespace=${org.name}`);
        // Should be denied — user is not a member of this org
        expect([401, 403]).toContain(r.status());
      });
    });

    // ========================================================================
    // Section 4 -- Anonymous access
    // ========================================================================

    test.describe('Anonymous access', () => {
      test('anonymous user gets 401', async () => {
        const r = await anonClient.get(HEALTH_URL);
        expect(r.status()).toBe(401);
      });
    });

    // ========================================================================
    // Section 5 -- Query parameters
    // ========================================================================

    test.describe('Query parameters', () => {
      test('namespace parameter filters results', async ({adminClient}) => {
        const r = await adminClient.get(
          `${HEALTH_URL}?namespace=${normalUsername}`,
        );
        expect([200, 503]).toContain(r.status());

        const body = await r.json();
        expect(body).toHaveProperty('healthy');
        expect(body).toHaveProperty('repositories');
      });

      test('detailed=true includes details and pagination', async ({
        adminClient,
      }) => {
        const r = await adminClient.get(`${HEALTH_URL}?detailed=true`);
        expect([200, 503]).toContain(r.status());

        const body = await r.json();
        expect(body.repositories).toHaveProperty('details');
        expect(Array.isArray(body.repositories.details)).toBe(true);
        expect(body.repositories).toHaveProperty('pagination');
        expect(body.repositories.pagination).toHaveProperty('limit');
        expect(body.repositories.pagination).toHaveProperty('offset');
        expect(body.repositories.pagination).toHaveProperty('has_more');
      });

      test('detailed=false omits details and pagination', async ({
        adminClient,
      }) => {
        const r = await adminClient.get(`${HEALTH_URL}?detailed=false`);
        expect([200, 503]).toContain(r.status());

        const body = await r.json();
        expect(body.repositories).not.toHaveProperty('details');
        expect(body.repositories).not.toHaveProperty('pagination');
      });

      test('limit and offset params accepted in detailed mode', async ({
        adminClient,
      }) => {
        const r = await adminClient.get(
          `${HEALTH_URL}?detailed=true&limit=5&offset=0`,
        );
        expect([200, 503]).toContain(r.status());

        const body = await r.json();
        expect(body.repositories.pagination.limit).toBe(5);
        expect(body.repositories.pagination.offset).toBe(0);
      });

      test('limit is clamped to max 1000', async ({adminClient}) => {
        const r = await adminClient.get(
          `${HEALTH_URL}?detailed=true&limit=9999`,
        );
        expect([200, 503]).toContain(r.status());

        const body = await r.json();
        expect(body.repositories.pagination.limit).toBeLessThanOrEqual(1000);
      });
    });

    // ========================================================================
    // Section 6 -- healthy vs unhealthy status codes
    // ========================================================================

    test.describe('Status code semantics', () => {
      test('healthy=true returns 200, healthy=false returns 503', async ({
        adminClient,
      }) => {
        const r = await adminClient.get(HEALTH_URL);
        const body = await r.json();

        if (body.healthy) {
          expect(r.status()).toBe(200);
        } else {
          expect(r.status()).toBe(503);
        }
      });
    });
  },
);
