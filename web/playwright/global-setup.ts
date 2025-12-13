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

import {chromium, FullConfig} from '@playwright/test';
import {API_URL} from './utils/config';
import {createUser} from './utils/api';

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

async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL || 'http://localhost:9000';

  console.log(
    `[Global Setup] Starting with baseURL: ${baseURL}, apiURL: ${API_URL}`,
  );

  let browser = null;

  try {
    browser = await chromium.launch();
    // Track failures to report at the end
    const failures: string[] = [];

    // Create test users (skip if they already exist)
    // Each user creation requires a fresh context and CSRF token
    for (const [role, user] of Object.entries(TEST_USERS)) {
      // Create a fresh context for each user to avoid CSRF token issues
      const userContext = await browser.newContext();
      const userRequest = userContext.request;

      try {
        console.log(`[Global Setup] Creating ${role} user: ${user.username}`);
        await createUser(userRequest, user.username, user.password, user.email);
        console.log(`[Global Setup] Created ${role} user: ${user.username}`);
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
        await userContext.close();
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
