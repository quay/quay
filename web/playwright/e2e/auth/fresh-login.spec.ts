import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe(
  'Fresh Login - Database auth password modal',
  {tag: ['@auth', '@auth:Database']},
  () => {
    test('shows password modal (not redirect) on fresh_login_required', async ({
      superuserPage: page,
    }) => {
      await page.route('**/api/v1/superuser/logs*', (route) =>
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({
            title: 'fresh_login_required',
            error_type: 'fresh_login_required',
            detail: 'The action requires a fresh login to succeed.',
            status: 401,
          }),
        }),
      );

      await page.goto('/usage-logs');

      await expect(page.getByText('Please Verify')).toBeVisible();
      await expect(page.locator('#fresh-password')).toBeVisible();
      await expect(
        page.getByText(/verify your password to perform this sensitive/),
      ).toBeVisible();

      // Database auth should NOT redirect to /signin
      expect(page.url()).not.toMatch(/\/signin/);
    });

    test('cancel dismisses the fresh-login modal', async ({
      superuserPage: page,
    }) => {
      await page.route('**/api/v1/superuser/logs*', (route) =>
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({
            title: 'fresh_login_required',
            error_type: 'fresh_login_required',
            detail: 'The action requires a fresh login to succeed.',
            status: 401,
          }),
        }),
      );

      await page.goto('/usage-logs');
      await expect(page.getByText('Please Verify')).toBeVisible();

      await page.getByRole('button', {name: 'Cancel'}).click();
      await expect(page.getByText('Please Verify')).not.toBeVisible();
    });

    test('successful password verification dismisses modal and retries', async ({
      superuserPage: page,
    }) => {
      let callCount = 0;
      await page.route('**/api/v1/superuser/logs*', async (route) => {
        callCount++;
        if (callCount === 1) {
          await route.fulfill({
            status: 401,
            contentType: 'application/json',
            body: JSON.stringify({
              title: 'fresh_login_required',
              error_type: 'fresh_login_required',
              detail: 'The action requires a fresh login to succeed.',
              status: 401,
            }),
          });
        } else {
          await route.continue();
        }
      });

      await page.goto('/usage-logs');
      await expect(page.getByText('Please Verify')).toBeVisible();

      await page.locator('#fresh-password').fill(TEST_USERS.admin.password);
      await page.getByRole('button', {name: 'Verify'}).click();

      // Modal should close after verification
      await expect(page.getByText('Please Verify')).not.toBeVisible({
        timeout: 10000,
      });

      // The logs page should load after the retry
      await expect(page.getByTestId('usage-logs-table')).toBeVisible({
        timeout: 10000,
      });
    });
  },
);
