import {defineConfig} from '@playwright/test';
import base from './billing-local.config';

// Existing regression paths affected by full-page organization creation.
export default defineConfig(base, {
  globalSetup: require.resolve('./billing-organization-setup'),
  testMatch: [
    '**/organization/contact-email.spec.ts',
    '**/organization/org-list.spec.ts',
    '**/ui/empty-states.spec.ts',
  ],
  grep: /Create Organization Page|create org with email|create org without email|FEATURE_MAILING no longer|create organization shows optional|organization CRUD lifecycle|shows success alert when creating an organization/,
  outputDir: '../test-results/billing-organization',
});
