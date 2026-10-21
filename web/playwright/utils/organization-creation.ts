import {expect, type Page} from '@playwright/test';

export async function selectFreeOrganizationPlan(page: Page): Promise<void> {
  const response = await page.request.get('/config');
  expect(response.ok()).toBe(true);
  const {features} = await response.json();
  if (features.BILLING) {
    await page.locator('#organization-plan-free').check();
  }
}
