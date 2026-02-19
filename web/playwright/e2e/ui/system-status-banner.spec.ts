/**
 * System Status Banner tests
 *
 * Tests the read-only mode and account recovery mode banners
 * that appear when the registry is in a special state.
 *
 * Uses page.route() to mock the /config endpoint since changing
 * registry state would affect all parallel tests.
 */

import {test as base, expect} from '../../fixtures';

const test = base;

test.describe('System Status Banner', {tag: ['@ui']}, () => {
  test('does not display banners in normal mode', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/organization');

    await expect(
      authenticatedPage.getByTestId('readonly-mode-banner'),
    ).not.toBeVisible();
    await expect(
      authenticatedPage.getByTestId('account-recovery-mode-banner'),
    ).not.toBeVisible();
  });

  test('displays read-only mode banner', async ({browser}) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.route('**/config', async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      body.registry_state = 'readonly';
      await route.fulfill({response, body: JSON.stringify(body)});
    });

    await page.goto('/organization');

    const banner = page.getByTestId('readonly-mode-banner');
    await expect(banner).toBeVisible();
    await expect(banner).toContainText('is currently in read-only mode');
    await expect(banner).toContainText(
      'Pulls and other read-only operations will succeed',
    );
    await expect(banner).toContainText(
      'all other operations are currently suspended',
    );
    // Registry name appears before the read-only text
    await expect(banner).toHaveText(/\S+\s+is currently in read-only mode/);

    await page.close();
    await context.close();
  });

  test('displays account recovery mode banner', async ({browser}) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.route('**/config', async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      body.account_recovery_mode = true;
      await route.fulfill({response, body: JSON.stringify(body)});
    });

    await page.goto('/organization');

    const banner = page.getByTestId('account-recovery-mode-banner');
    await expect(banner).toBeVisible();
    await expect(banner).toContainText('is currently in account recovery mode');
    await expect(banner).toContainText(
      'This instance should only be used to link accounts',
    );
    await expect(banner).toContainText(
      'Registry operations such as pushes/pulls will not work',
    );

    await page.close();
    await context.close();
  });

  test('displays both banners when both modes are active', async ({
    browser,
  }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.route('**/config', async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      body.registry_state = 'readonly';
      body.account_recovery_mode = true;
      await route.fulfill({response, body: JSON.stringify(body)});
    });

    // Verify banners on organization page
    await page.goto('/organization');
    await expect(page.getByTestId('readonly-mode-banner')).toBeVisible();
    await expect(
      page.getByTestId('account-recovery-mode-banner'),
    ).toBeVisible();

    // Verify banners persist across navigation
    await page.goto('/repository');
    await expect(page.getByTestId('readonly-mode-banner')).toBeVisible();

    await page.close();
    await context.close();
  });
});
