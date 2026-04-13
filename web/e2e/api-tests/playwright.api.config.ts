import {defineConfig} from '@playwright/test';

/**
 * Playwright configuration for API-only tests.
 *
 * These tests exercise the Quay REST API without a browser. They run serially
 * within each spec file because many tests depend on state created by earlier
 * tests (e.g. create org → create repo inside org → verify permissions).
 */
export default defineConfig({
  testDir: './suites',

  // No global setup — each suite initializes its own users via the API.
  // The Quay instance must already be running with FEATURE_USER_INITIALIZE.

  // Serial execution within each file (tests share state)
  fullyParallel: false,
  workers: 1,

  // Timeout per test — some API calls (mirror sync, image push) are slow
  timeout: 60_000,

  // Fail the build on CI if test.only is left in source
  forbidOnly: !!process.env.CI,

  // No retries — serial tests can't meaningfully retry mid-sequence
  retries: 0,

  reporter: [
    [process.env.CI ? 'github' : 'list'],
    ['json', {outputFile: 'test-results/api-results.json'}],
  ],

  use: {
    // No browser — pure API testing via request contexts
    ignoreHTTPSErrors: true,
    extraHTTPHeaders: {
      'Content-Type': 'application/json',
    },
  },

  // No browser projects — API tests use request contexts only
  projects: [
    {
      name: 'api',
      use: {
        baseURL: process.env.QUAY_API_URL || 'http://localhost:8080',
      },
    },
  ],
});
