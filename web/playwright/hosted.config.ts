import {defineConfig, devices} from '@playwright/test';

if (!process.env.QUAY_HOSTED_NAMESPACE) {
  throw new Error(
    'Set QUAY_HOSTED_NAMESPACE to the Quay.io namespace to inspect.',
  );
}

// Separate from the full Quay suite: these checks only read a hosted account.
export default defineConfig({
  testDir: './e2e/billing',
  testMatch: 'hosted-billing.spec.ts',
  workers: 1,
  timeout: 60000,
  outputDir: '/private/tmp/quay-hosted-billing-results',
  reporter: 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://localhost:9010',
    channel: process.env.PLAYWRIGHT_CHANNEL,
    ignoreHTTPSErrors: true,
    // Hosted responses contain real account information; avoid recording traces.
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
  projects: [{name: 'chromium', use: {...devices['Desktop Chrome']}}],
});
