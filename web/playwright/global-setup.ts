/**
 * Playwright Global Setup
 *
 * This runs ONCE before all tests to set up the test environment.
 * Creates initial test users that will be used across all test runs.
 *
 * Users created:
 * - testuser: Regular user for standard tests
 * - admin: Superuser for admin tests
 * - readonly: User with read-only access (if applicable)
 */

import {
  APIRequestContext,
  chromium,
  FullConfig,
  request,
} from '@playwright/test';
import {API_URL} from './utils/config';
import {ApiClient} from './utils/api';
import {mailpit} from './utils/mailpit';
import {fetchJsonWithRetry, setFetchImpl} from './utils/fetch-retry';
import type {FetchImpl} from './utils/fetch-retry';
import {applyChromiumLoopbackBypass, proxyOptionFromEnv} from './utils/proxy';
import type {QuayConfig} from './fixtures';

/**
 * Build a fetch implementation backed by a Playwright APIRequestContext.
 *
 * Native `fetch` (undici) ignores HTTP(S)_PROXY, so when Quay is only reachable
 * through a proxy (bare-metal CI) global-setup's config/mailpit calls fail with
 * ENOTFOUND. Playwright's request context honors the `proxy` option and
 * `ignoreHTTPSErrors`, so route the retry helpers through it instead.
 */
function requestFetchImpl(context: APIRequestContext): FetchImpl {
  return async (url, init, timeoutMs) => {
    const method = (init?.method ?? 'GET').toString();
    const response = await context.fetch(url, {
      method,
      timeout: timeoutMs,
      headers: init?.headers as Record<string, string> | undefined,
      data: init?.body as string | undefined,
    });
    return {
      ok: response.ok(),
      status: response.status(),
      json: () => response.json(),
    };
  };
}

export type TestUser = {
  username: string;
  password: string;
  email: string;
};
export type TestUsers = {
  readonly admin: TestUser;
  readonly user: TestUser;
  readonly readonly: TestUser;
};

// Users for Database auth. Created by globalSetup in that mode.
const TEST_USERS_DATABASE: TestUsers = {
  // Admin/superuser for admin operations
  admin: {
    username: 'admin',
    password: 'password',
    email: 'admin@example.com',
  },
  // Regular user for standard operations
  user: {
    username: 'testuser',
    password: 'password',
    email: 'testuser@example.com',
  },
  // Readonly user for permission tests
  readonly: {
    username: 'readonly',
    password: 'password',
    email: 'readonly@example.com',
  },
};

// Separate OIDC test users to avoid naming collisions with Database-auth users.
// OIDCUsers.get_user() returns None, so LOGIN_BINDING_FIELD doesn't work —
// first OIDC login always creates a new Quay account. Using distinct usernames
// ensures clean creation regardless of whether DB users already exist.
export const TEST_USERS_OIDC: TestUsers = {
  admin: {
    username: 'admin_oidc',
    password: 'password',
    email: 'admin_oidc@example.com',
  },
  user: {
    username: 'testuser_oidc',
    password: 'password',
    email: 'testuser_oidc@example.com',
  },
  readonly: {
    username: 'readonly_oidc',
    password: 'password',
    email: 'readonly_oidc@example.com',
  },
};

// Separate LDAP test users to avoid naming collisions with Database-auth users.
// LDAP first-login creates a federated user entry; if the username or email
// is already taken by a Database-phase user, creation fails. Using distinct
// usernames/emails ensures clean federated user creation.
export const TEST_USERS_LDAP: TestUsers = {
  admin: {
    username: 'admin_ldap',
    password: 'password',
    email: 'admin_ldap@example.com',
  },
  user: {
    username: 'testuser_ldap',
    password: 'password',
    email: 'testuser_ldap@example.com',
  },
  readonly: {
    username: 'readonly_ldap',
    password: 'password',
    email: 'readonly_ldap@example.com',
  },
};

// Resolve the user set for the current auth mode. globalSetup sets
// QUAY_AUTH_TYPE from Quay's /config before any worker starts (the same
// env-inheritance path QUAY_CONFIG_JSON already relies on), so this resolves
// correctly wherever specs access it -- including module- and describe-level
// code, which is why specs can keep importing TEST_USERS statically instead
// of threading getTestUsers() through every fixture. Before globalSetup runs
// (e.g. test discovery, --list), it falls back to the Database users.
function currentTestUsers(): TestUsers {
  const authType = process.env.QUAY_AUTH_TYPE;
  if (authType === 'OIDC') return TEST_USERS_OIDC;
  if (authType === 'LDAP') return TEST_USERS_LDAP;
  return TEST_USERS_DATABASE;
}

// Auth-aware stand-in for the former `export const TEST_USERS = {...}`.
// Specs that statically import TEST_USERS previously always got the Database
// usernames (testuser/readonly/admin) even under OIDC/LDAP, where the logged-in
// sessions belong to testuser_oidc/... — causing 403 insufficient_scope on
// repo creation, 401s on registry basic auth with Database credentials, and
// UI timeouts on /user/<database-username> pages (see the OIDC full-suite
// RCA in .cursor/oidc-testing). Property access resolves per auth mode, so
// e.g. TEST_USERS.user.username yields 'testuser' under Database auth,
// 'testuser_oidc' under OIDC, and 'testuser_ldap' under LDAP.
export const TEST_USERS = {
  get admin(): TestUser {
    return currentTestUsers().admin;
  },
  get user(): TestUser {
    return currentTestUsers().user;
  },
  get readonly(): TestUser {
    return currentTestUsers().readonly;
  },
};

async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL || 'http://localhost:8080';

  // When Quay is reachable only through a proxy (bare-metal CI), route every
  // global-setup network call through a Playwright request context configured
  // with the proxy env vars. Native fetch() ignores HTTP(S)_PROXY. No-op
  // locally where no proxy env is set.
  // Keep localhost (mailpit, local webserver) direct when a proxy is set,
  // before the email-confirmation Chromium launch below.
  applyChromiumLoopbackBypass();
  const proxy = proxyOptionFromEnv();
  const setupRequestContext = await request.newContext({
    ignoreHTTPSErrors: true,
    ...(proxy ? {proxy} : {}),
  });
  setFetchImpl(requestFetchImpl(setupRequestContext));

  console.log(
    `[Global Setup] Starting with baseURL: ${baseURL}, apiURL: ${API_URL}`,
  );

  // Only launch browser if needed for email confirmation (rare path)
  let browser: Awaited<ReturnType<typeof chromium.launch>> | null = null;

  try {
    // Track failures to report at the end
    const failures: string[] = [];

    // Fetch Quay config with retry to check auth type and features. Quay
    // may not be listening yet at this point (this is the boot-wait path),
    // so use a longer backoff than the default to give it time to come up.
    const quayConfig = await fetchJsonWithRetry<QuayConfig>(
      'global-setup config fetch',
      `${API_URL}/config`,
      undefined,
      undefined,
      [2000, 2000],
    );
    const mailingEnabled = quayConfig?.features?.MAILING === true;
    const authType =
      (quayConfig?.config?.AUTHENTICATION_TYPE as string | undefined) ||
      'Database';
    process.env.QUAY_CONFIG_JSON = JSON.stringify(quayConfig);
    // Read by the lazy TEST_USERS getters (see currentTestUsers) so that
    // statically-imported TEST_USERS in specs resolves to the auth-mode user
    // set inside workers. Safe to overwrite on re-runs.
    process.env.QUAY_AUTH_TYPE = authType;

    // For OIDC auth, skip user creation — users are created on first login
    // via the Keycloak browser flow in the worker fixtures (loginViaOIDC).
    if (authType !== 'Database') {
      console.log(
        `[Global Setup] Auth type is '${authType}', skipping user creation (OIDC users created on first login via worker fixtures)`,
      );
      console.log('[Global Setup] Complete');
      return;
    }

    // Check if Mailpit is available when mailing is enabled
    const mailpitAvailable = mailingEnabled && (await mailpit.isAvailable());
    if (mailingEnabled) {
      console.log(
        `[Global Setup] FEATURE_MAILING enabled, Mailpit ${
          mailpitAvailable ? 'available' : 'NOT available'
        }`,
      );
      if (mailpitAvailable) {
        await mailpit.clearInbox();
      }
    }

    // Create test users (skip if they already exist)
    // Each user creation requires a fresh request context and CSRF token
    for (const [role, user] of Object.entries(TEST_USERS)) {
      const requestContext = await request.newContext({
        ignoreHTTPSErrors: true,
        ...(proxy ? {proxy} : {}),
      });

      try {
        console.log(`[Global Setup] Creating ${role} user: ${user.username}`);
        const api = new ApiClient(requestContext);

        try {
          await api.createUser(user.username, user.password, user.email);
          console.log(`[Global Setup] Created ${role} user: ${user.username}`);
        } catch (error) {
          const errorMessage = String(error);
          if (
            errorMessage.includes('already exists') ||
            errorMessage.includes('already taken')
          ) {
            console.log(
              `[Global Setup] ${role} user already exists: ${user.username}`,
            );
          } else {
            throw error;
          }
        }

        // Verify email before signing in — sign-in returns 403 when
        // needsEmailVerification is true.
        if (mailpitAvailable) {
          console.log(
            `[Global Setup] Verifying email for ${role} user: ${user.email}`,
          );
          const confirmLink = await mailpit.waitForConfirmationLink(user.email);
          if (confirmLink) {
            if (!browser) {
              browser = await chromium.launch(proxy ? {proxy} : {});
            }
            const context = await browser.newContext({
              ignoreHTTPSErrors: true,
              ...(proxy ? {proxy} : {}),
            });
            const page = await context.newPage();
            await page.goto(confirmLink);
            await page.close();
            await context.close();
            console.log(
              `[Global Setup] Email verified for ${role} user: ${user.username}`,
            );
          } else {
            console.warn(
              `[Global Setup] No confirmation email found for ${user.email}`,
            );
          }
        }

        // Clear user prompts (enter_name, enter_company) so tests aren't
        // redirected to /updateuser when USER_METADATA is enabled.
        await api.signIn(user.username, user.password);
        await api.clearUserPrompts();
      } catch (error) {
        console.error(`[Global Setup] Error creating ${role} user: ${error}`);
        failures.push(`${role} (${user.username}): ${error}`);
      } finally {
        await requestContext.dispose();
      }
    }

    // Fail if any required users could not be created
    if (failures.length > 0) {
      throw new Error(
        `Global setup failed: Could not create required test users:\n  - ${failures.join(
          '\n  - ',
        )}`,
      );
    }

    console.log('[Global Setup] Complete');
  } catch (error) {
    console.error('[Global Setup] Failed:', error);
    throw error;
  } finally {
    // Restore native fetch so later Playwright phases aren't bound to the
    // disposed setup context, then dispose it.
    setFetchImpl();
    await setupRequestContext.dispose();
    if (browser) {
      await browser.close();
    }
  }
}

export default globalSetup;
