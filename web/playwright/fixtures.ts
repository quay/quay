/**
 * Playwright Custom Fixtures
 *
 * Provides pre-authenticated contexts for different user roles.
 * Tests can extend these fixtures to get logged-in sessions.
 *
 * @example
 * ```typescript
 * import { test, expect } from '../fixtures';
 *
 * test('can view organization', async ({ authenticatedPage }) => {
 *   await authenticatedPage.goto('/organization');
 *   await expect(authenticatedPage.getByText('Organizations')).toBeVisible();
 * });
 *
 * test('superuser can manage users', async ({ superuserPage }) => {
 *   await superuserPage.goto('/superuser');
 *   await expect(superuserPage.getByText('Users')).toBeVisible();
 * });
 * ```
 */

import {
  test as base,
  expect,
  Page,
  APIRequestContext,
  BrowserContext,
} from '@playwright/test';
import {TEST_USERS} from './global-setup';
import {API_URL} from './utils/config';
import {getCsrfToken} from './utils/api';

// ============================================================================
// Quay Config Types
// ============================================================================

/**
 * Known Quay feature flags that can be enabled/disabled
 */
export type QuayFeature =
  | 'BILLING'
  | 'QUOTA_MANAGEMENT'
  | 'EDIT_QUOTA'
  | 'AUTO_PRUNE'
  | 'PROXY_CACHE'
  | 'REPO_MIRROR'
  | 'SECURITY_SCANNER'
  | 'CHANGE_TAG_EXPIRATION'
  | 'USER_METADATA'
  | 'MAILING';

/**
 * Quay configuration from /config endpoint
 */
export interface QuayConfig {
  features: Partial<Record<QuayFeature, boolean>>;
  config: Record<string, unknown>;
}

/**
 * Helper to skip tests when required features are not enabled.
 * Returns a tuple that can be spread into test.skip()
 *
 * @example
 * ```typescript
 * test('requires billing', async ({ quayConfig }) => {
 *   test.skip(...skipUnlessFeature(quayConfig, 'BILLING'));
 *   // test code...
 * });
 *
 * test('requires multiple features', async ({ quayConfig }) => {
 *   test.skip(...skipUnlessFeature(quayConfig, 'QUOTA_MANAGEMENT', 'EDIT_QUOTA'));
 *   // test code...
 * });
 * ```
 */
export function skipUnlessFeature(
  config: QuayConfig | null,
  ...features: QuayFeature[]
): [boolean, string] {
  const missing = features.filter((f) => !config?.features?.[f]);
  if (missing.length === 0) return [false, ''];
  return [true, `Required feature(s) not enabled: ${missing.join(', ')}`];
}

/**
 * Login a user and return the CSRF token
 */
async function loginUser(
  request: APIRequestContext,
  username: string,
  password: string,
): Promise<string> {
  const csrfToken = await getCsrfToken(request);

  const response = await request.post(`${API_URL}/api/v1/signin`, {
    headers: {'X-CSRF-Token': csrfToken},
    data: {username, password},
  });

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(
      `Login failed for ${username}: ${response.status()} - ${body}`,
    );
  }

  return csrfToken;
}

/**
 * Extended test fixtures providing authenticated contexts
 */
type TestFixtures = {
  // CSRF token for API calls (after login)
  csrfToken: string;

  // Pre-authenticated page as regular user
  authenticatedPage: Page;

  // Pre-authenticated page as superuser
  superuserPage: Page;

  // Pre-authenticated page as readonly user
  readonlyPage: Page;

  // Pre-authenticated API request context as regular user
  authenticatedRequest: APIRequestContext;

  // Pre-authenticated API request context as superuser
  superuserRequest: APIRequestContext;

  // Quay configuration (features, config settings)
  quayConfig: QuayConfig;
};

/**
 * Worker fixtures (shared across tests in same worker)
 */
type WorkerFixtures = {
  // Browser context with regular user auth
  userContext: BrowserContext;

  // Browser context with superuser auth
  superuserContext: BrowserContext;

  // Browser context with readonly user auth
  readonlyContext: BrowserContext;

  // Cached Quay config (fetched once per worker)
  cachedQuayConfig: QuayConfig;
};

/**
 * Extended test with custom fixtures
 */
export const test = base.extend<TestFixtures, WorkerFixtures>({
  // =========================================================================
  // Worker-scoped fixtures (created once per worker)
  // =========================================================================

  userContext: [
    async ({browser}, use) => {
      const context = await browser.newContext();
      const request = context.request;

      // Login as regular user
      await loginUser(
        request,
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await use(context);
      await context.close();
    },
    {scope: 'worker'},
  ],

  superuserContext: [
    async ({browser}, use) => {
      const context = await browser.newContext();
      const request = context.request;

      // Login as admin (superuser)
      await loginUser(
        request,
        TEST_USERS.admin.username,
        TEST_USERS.admin.password,
      );

      await use(context);
      await context.close();
    },
    {scope: 'worker'},
  ],

  readonlyContext: [
    async ({browser}, use) => {
      const context = await browser.newContext();
      const request = context.request;

      // Login as readonly user
      await loginUser(
        request,
        TEST_USERS.readonly.username,
        TEST_USERS.readonly.password,
      );

      await use(context);
      await context.close();
    },
    {scope: 'worker'},
  ],

  cachedQuayConfig: [
    async ({browser}, use) => {
      // Create a temporary context just to fetch config
      const context = await browser.newContext();
      const response = await context.request.get(`${API_URL}/config`);
      if (!response.ok()) {
        await context.close();
        throw new Error(`Failed to fetch Quay config: ${response.status()}`);
      }
      const config = (await response.json()) as QuayConfig;
      await context.close();
      await use(config);
    },
    {scope: 'worker'},
  ],

  // =========================================================================
  // Test-scoped fixtures (created fresh for each test)
  // =========================================================================

  csrfToken: async ({request}, use) => {
    const token = await loginUser(
      request,
      TEST_USERS.user.username,
      TEST_USERS.user.password,
    );
    await use(token);
  },

  authenticatedPage: async ({userContext}, use) => {
    const page = await userContext.newPage();
    await use(page);
    await page.close();
  },

  superuserPage: async ({superuserContext}, use) => {
    const page = await superuserContext.newPage();
    await use(page);
    await page.close();
  },

  readonlyPage: async ({readonlyContext}, use) => {
    const page = await readonlyContext.newPage();
    await use(page);
    await page.close();
  },

  authenticatedRequest: async ({userContext}, use) => {
    await use(userContext.request);
  },

  superuserRequest: async ({superuserContext}, use) => {
    await use(superuserContext.request);
  },

  quayConfig: async ({cachedQuayConfig}, use) => {
    await use(cachedQuayConfig);
  },
});

// Re-export expect for convenience
export {expect};

/**
 * Utility to generate unique names for test resources
 */
export function uniqueName(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random()
    .toString(36)
    .substring(2, 8)}`;
}
