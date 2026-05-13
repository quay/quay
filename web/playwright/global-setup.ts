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

import {chromium, FullConfig, request} from '@playwright/test';
import {API_URL} from './utils/config';
import {ApiClient} from './utils/api';
import {mailpit} from './utils/mailpit';

export const TEST_USERS = {
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
} as const;

// Separate OIDC test users to avoid naming collisions with Database-auth users.
// OIDCUsers.get_user() returns None, so LOGIN_BINDING_FIELD doesn't work —
// first OIDC login always creates a new Quay account. Using distinct usernames
// ensures clean creation regardless of whether DB users already exist.
export const TEST_USERS_OIDC = {
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
} as const;

// Separate LDAP test users to avoid naming collisions with Database-auth users.
// LDAP first-login creates a federated user entry; if the username or email
// is already taken by a Database-phase user, creation fails. Using distinct
// usernames/emails ensures clean federated user creation.
export const TEST_USERS_LDAP = {
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
} as const;

async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL || 'http://localhost:8080';

  console.log(
    `[Global Setup] Starting with baseURL: ${baseURL}, apiURL: ${API_URL}`,
  );

  // Only launch browser if needed for email confirmation (rare path)
  let browser: Awaited<ReturnType<typeof chromium.launch>> | null = null;

  try {
    // Track failures to report at the end
    const failures: string[] = [];

    // Fetch Quay config with retry to check auth type and features
    let mailingEnabled = false;
    let authType: string | undefined;
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const configResponse = await fetch(`${API_URL}/config`);
        if (configResponse.ok) {
          const quayConfig = await configResponse.json();
          mailingEnabled = quayConfig?.features?.MAILING === true;
          authType = quayConfig?.config?.AUTHENTICATION_TYPE || 'Database';
          process.env.QUAY_CONFIG_JSON = JSON.stringify(quayConfig);
          break;
        }
      } catch {
        console.log(
          `[Global Setup] Config fetch attempt ${
            attempt + 1
          }/3 failed, retrying...`,
        );
        await new Promise((r) => setTimeout(r, 2000));
      }
    }
    if (!authType) {
      throw new Error(
        '[Global Setup] Failed to fetch Quay config after 3 attempts',
      );
    }

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
      });

      try {
        console.log(`[Global Setup] Creating ${role} user: ${user.username}`);
        const api = new ApiClient(requestContext);
        await api.createUser(user.username, user.password, user.email);
        console.log(`[Global Setup] Created ${role} user: ${user.username}`);

        // Verify email if mailing is enabled and Mailpit is available
        if (mailpitAvailable) {
          console.log(
            `[Global Setup] Verifying email for ${role} user: ${user.email}`,
          );
          const confirmLink = await mailpit.waitForConfirmationLink(user.email);
          if (confirmLink) {
            // Email confirmation requires visiting a link — need a browser
            if (!browser) {
              browser = await chromium.launch();
            }
            const context = await browser.newContext({
              ignoreHTTPSErrors: true,
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
      } catch (error) {
        const errorMessage = String(error);
        // User might already exist (400 error with "already exists")
        if (
          errorMessage.includes('already exists') ||
          errorMessage.includes('already taken')
        ) {
          console.log(
            `[Global Setup] ${role} user already exists: ${user.username}`,
          );
        } else {
          console.error(`[Global Setup] Error creating ${role} user: ${error}`);
          failures.push(`${role} (${user.username}): ${error}`);
        }
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
    if (browser) {
      await browser.close();
    }
  }
}

export default globalSetup;
