import {defineConfig, devices} from '@playwright/test';

// Preview checks run against the app's built-in MOCK_API data. The real Quay
// blackbox suite keeps its own configuration, fixtures, and backend setup.
export default defineConfig({
  testDir: './prototype',
  fullyParallel: true,
  workers: 2,
  timeout: 60000,
  outputDir: '/private/tmp/quay-billing-prototype-results',
  reporter: 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:9010',
    channel: process.env.PLAYWRIGHT_CHANNEL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: {width: 1440, height: 1000},
      },
    },
  ],
});
