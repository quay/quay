/**
 * Playwright fixtures for API-only tests.
 *
 * Provides pre-authenticated API request contexts for different user roles
 * and RawApiClient instances for asserting on status codes. No browser
 * contexts are created — these tests are pure HTTP.
 *
 * Usage:
 * ```typescript
 * import {test, expect} from '../fixtures';
 *
 * test('admin can create org', async ({adminClient}) => {
 *   const response = await adminClient.post('/api/v1/organization/', {
 *     name: 'test-org',
 *     email: 'test@example.com',
 *   });
 *   expect(response.status()).toBe(200);
 * });
 * ```
 */

import {test as base, expect} from '@playwright/test';

import {requestCsrfToken} from '../shared/csrf';
import {uniqueName} from '../shared/test-utils';
import {RawApiClient} from '../utils/api/raw-client';
import {initializeSuperuser} from '../utils/api/auth';

// Default credentials — matching the existing CI setup
const ADMIN = {
  username: process.env.QUAY_ADMIN_USERNAME || 'admin',
  password: process.env.QUAY_ADMIN_PASSWORD || 'password',
  email: process.env.QUAY_ADMIN_EMAIL || 'admin@example.com',
};

// Test user with a known password — created via self-registration API
const TEST_USER = {
  username: 'apitest_user',
  password: 'apitestpass123',
  email: 'apitest_user@example.com',
};

/**
 * Get the Quay API base URL from the test configuration.
 */
function getBaseUrl(): string {
  return process.env.QUAY_API_URL || 'http://localhost:8080';
}

type ApiTestFixtures = {
  /** Base URL for the Quay API */
  baseUrl: string;

  /** RawApiClient authenticated as admin/superuser */
  adminClient: RawApiClient;

  /** RawApiClient authenticated as a normal (non-admin) user */
  userClient: RawApiClient;

  /** Unauthenticated RawApiClient (no session) */
  anonClient: RawApiClient;
};

type ApiWorkerFixtures = {
  /** Ensures the admin user is initialized (once per worker) */
  _adminInitialized: void;

  /** Ensures a test user exists (once per worker) */
  _testUserInitialized: string; // returns the test user's password
};

export const test = base.extend<ApiTestFixtures, ApiWorkerFixtures>({
  // =========================================================================
  // Worker-scoped fixtures (run once per worker)
  // =========================================================================

  _adminInitialized: [
    async ({playwright}, use) => {
      const baseUrl = process.env.QUAY_API_URL || 'http://localhost:8080';
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });

      try {
        try {
          await initializeSuperuser(
            request,
            baseUrl,
            ADMIN.username,
            ADMIN.password,
            ADMIN.email,
          );
        } catch (e) {
          // Only ignore "already initialized" — surface real bootstrap failures
          if (!(e instanceof Error && e.message.includes('already'))) {
            throw e;
          }
        }

        await use();
      } finally {
        await request.dispose();
      }
    },
    {scope: 'worker'},
  ],

  _testUserInitialized: [
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    async ({playwright, _adminInitialized}, use) => {
      const baseUrl = process.env.QUAY_API_URL || 'http://localhost:8080';

      // Create the test user via self-registration (POST /api/v1/user/)
      // This lets us specify the password, unlike the superuser API which
      // auto-generates one. Idempotent — silently succeeds if user exists.
      const request = await playwright.request.newContext({
        ignoreHTTPSErrors: true,
      });

      try {
        const csrfToken = await requestCsrfToken(request, baseUrl);

        const response = await request.post(`${baseUrl}/api/v1/user/`, {
          headers: {'X-CSRF-Token': csrfToken},
          data: {
            username: TEST_USER.username,
            password: TEST_USER.password,
            email: TEST_USER.email,
          },
        });

        if (response.ok()) {
          // User created successfully
        } else {
          const body = await response.text();
          if (!body.includes('already')) {
            throw new Error(
              `Failed to create test user: ${response.status()} - ${body}`,
            );
          }
          // User already exists — password is already known
        }
      } finally {
        await request.dispose();
      }

      await use(TEST_USER.password);
    },
    {scope: 'worker'},
  ],

  // =========================================================================
  // Test-scoped fixtures (fresh per test)
  // =========================================================================

  // eslint-disable-next-line no-empty-pattern
  baseUrl: async ({}, use) => {
    await use(getBaseUrl());
  },

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  adminClient: async ({playwright, _adminInitialized, baseUrl}, use) => {
    const request = await playwright.request.newContext({
      ignoreHTTPSErrors: true,
    });
    try {
      const client = new RawApiClient(request, baseUrl);
      await client.signIn(ADMIN.username, ADMIN.password);
      await use(client);
    } finally {
      await request.dispose();
    }
  },

  userClient: async (
    {playwright, _testUserInitialized: password, baseUrl},
    use,
  ) => {
    const request = await playwright.request.newContext({
      ignoreHTTPSErrors: true,
    });
    try {
      const client = new RawApiClient(request, baseUrl);
      await client.signIn(TEST_USER.username, password);
      await use(client);
    } finally {
      await request.dispose();
    }
  },

  anonClient: async ({playwright, baseUrl}, use) => {
    const request = await playwright.request.newContext({
      ignoreHTTPSErrors: true,
    });
    try {
      const client = new RawApiClient(request, baseUrl);
      await use(client);
    } finally {
      await request.dispose();
    }
  },
});

export {expect};
export {uniqueName} from '../shared/test-utils';
