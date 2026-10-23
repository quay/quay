import {defineConfig, devices} from '@playwright/test';

// Uses a session from the deployment under test, without the development OAuth proxy.
export default defineConfig({
  testDir: './e2e/billing',
  testMatch: 'native-checkout.spec.ts',
  workers: 1,
  timeout: 60000,
  outputDir: '../test-results/native-billing',
  reporter: 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:9010',
    storageState: process.env.QUAY_BILLING_STORAGE_STATE,
    channel: process.env.PLAYWRIGHT_CHANNEL,
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
  projects: [{name: 'chromium', use: {...devices['Desktop Chrome']}}],
});
