import {defineConfig, devices} from '@playwright/test';
import base from '../playwright.config';

// These specs provision their own accounts through the public API.
export default defineConfig(base, {
  testDir: './e2e',
  testMatch: [
    '**/billing/plan-selection.spec.ts',
    '**/organization/create-organization.spec.ts',
    '**/billing/fake-checkout.spec.ts',
    '**/api/fake-checkout.spec.ts',
    '**/billing/accessibility.spec.ts',
  ],
  outputDir: '../test-results/billing-local',
  globalSetup: require.resolve('./billing-local-setup'),
  workers: 1,
  webServer: undefined,
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        channel: process.env.PLAYWRIGHT_CHANNEL || 'chromium',
      },
    },
  ],
});
