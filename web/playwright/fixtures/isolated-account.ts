import type {BrowserContext, Page} from '@playwright/test';
import {test as base, expect, TestApi, uniqueName} from '../fixtures';
import {ApiClient} from '../utils/api';
import {API_URL} from '../utils/config';

type BillingAccount = {
  username: string;
  context: BrowserContext;
  client: ApiClient;
};

export const test = base.extend<{
  billingPage: Page;
  billingAccount: BillingAccount;
}>({
  billingAccount: async ({browser, baseURL, quayConfig}, use) => {
    test.skip(
      quayConfig.config.AUTHENTICATION_TYPE !== 'Database' ||
        quayConfig.features.MAILING,
      'These isolated-account tests require Database authentication without email verification.',
    );
    const context = await browser.newContext({baseURL});
    const client = new ApiClient(context.request);
    const username = uniqueName('billing');
    const password = 'QUAY_FIXTURE_ONLY-Billing123';
    await client.createUser(username, password, `${username}@example.com`);
    await client.signIn(username, password);
    client.setCredentials(username, password);
    await client.clearUserPrompts();
    try {
      await use({username, context, client});
    } finally {
      try {
        await client.signIn(username, password);
        const response = await context.request.delete(
          `${API_URL}/api/v1/user/`,
          {
            headers: {'X-CSRF-Token': await client.getToken()},
          },
        );
        expect(response.ok()).toBe(true);
      } finally {
        await context.close();
      }
    }
  },
  api: async ({billingAccount}, use) => {
    const api = new TestApi(billingAccount.client, billingAccount.username);
    try {
      await use(api);
    } finally {
      await api.cleanup();
    }
  },
  authenticatedPage: async ({billingPage}, use) => use(billingPage),
  authenticatedRequest: async ({billingAccount}, use) =>
    use(billingAccount.context.request),
  billingPage: async ({billingAccount}, use) => {
    const page = await billingAccount.context.newPage();
    try {
      await use(page);
    } finally {
      await page.close();
    }
  },
});

export {expect, uniqueName} from '../fixtures';
