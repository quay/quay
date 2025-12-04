import {defineConfig, devices} from '@playwright/test';

/**
 * Playwright configuration for Quay E2E tests
 * See https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './playwright/e2e',

  // Global setup to create test users before all tests
  globalSetup: require.resolve('./playwright/global-setup'),

  // Maximum time one test can run for
  timeout: 60 * 1000,

  // Run tests in parallel (auto-detect optimal worker count based on CPU cores)
  fullyParallel: true,
  workers: undefined,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 1 : 0,

  // Reporter configuration
  reporter: [
    [process.env.CI ? 'github' : 'list'],
    ['html', {outputFolder: 'playwright-report'}],
    ['json', {outputFile: 'test-results/results.json'}],
  ],

  // Shared settings for all tests
  use: {
    // Base URL for navigation
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:9000',

    // Action timeout
    actionTimeout: 30 * 1000,

    // Collect trace only on failure
    trace: 'on-first-retry',

    // Screenshot only on failure
    screenshot: 'only-on-failure',

    // Video only on failure
    video: 'retain-on-failure',
  },

  // Output directories
  outputDir: 'test-results/',

  // Configure projects for different browsers
  // In CI, run all browsers; locally, just chromium for speed
  projects: process.env.CI
    ? [
        {
          name: 'chromium',
          use: {...devices['Desktop Chrome']},
        },
        {
          name: 'firefox',
          use: {...devices['Desktop Firefox']},
        },
        {
          name: 'webkit',
          use: {...devices['Desktop Safari']},
        },
      ]
    : [
        {
          name: 'chromium',
          use: {...devices['Desktop Chrome']},
        },
      ],

  // Configure web server for local development
  // Note: In CI, services are started separately via docker-compose
  webServer: {
    command:
      'REACT_QUAY_APP_API_URL=http://localhost:8080 npm run build && npm run start:integration',
    url: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:9000',
    reuseExistingServer: true,
    timeout: 120 * 1000,
  },
});
