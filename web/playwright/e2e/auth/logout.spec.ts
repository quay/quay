import {test as base, expect, type IsolatedUserSlot} from '../../fixtures';
import type {BrowserContext, Page} from '@playwright/test';
import {ApiClient} from '../../utils/api';

/**
 * Logout tests use one isolated user per test to avoid session invalidation conflicts.
 *
 * Background: Quay's /api/v1/signout endpoint calls `invalidate_all_sessions(user)`
 * which invalidates ALL sessions for that user across all browser contexts.
 * This would cause parallel tests using the same user to fail.
 */

interface LogoutTestFixtures {
  /** Opens a page signed in as the slot's isolated user - safe to logout */
  logoutUser: (
    slot: IsolatedUserSlot,
  ) => Promise<{page: Page; username: string}>;
}

const test = base.extend<LogoutTestFixtures>({
  logoutUser: async ({browser, isolatedUser}, use) => {
    const contexts: BrowserContext[] = [];

    await use(async (slot) => {
      const {user} = await isolatedUser(slot);
      const context = await browser.newContext();
      contexts.push(context);
      await new ApiClient(context.request).signIn(user.username, user.password);
      return {page: await context.newPage(), username: user.username};
    });

    for (const context of contexts) {
      await context.close();
    }
  },
});

test.describe('Logout functionality', {tag: ['@auth', '@critical']}, () => {
  test('logs out successfully', {tag: '@superuser'}, async ({logoutUser}) => {
    const {page: logoutPage} = await logoutUser('logout-success');

    // Navigate to organization page (where a logged-in user would be)
    await logoutPage.goto('/organization');
    await expect(logoutPage).toHaveURL(/\/organization/);

    // Verify user menu is visible (confirms we're logged in)
    await expect(logoutPage.getByTestId('user-menu-toggle')).toBeVisible();

    // Click user menu
    await logoutPage.getByTestId('user-menu-toggle').click();

    // Click logout
    await logoutPage.getByRole('menuitem', {name: 'Logout'}).click();

    // Should redirect to signin page
    await expect(logoutPage).toHaveURL(/\/signin/);
  });

  test(
    'redirects to signin even when logout API fails',
    {tag: '@superuser'},
    async ({logoutUser}) => {
      const {page: logoutPage} = await logoutUser('logout-error');

      // Mock API to return 500 error - this is an acceptable mock for error scenarios
      await logoutPage.route('**/api/v1/signout', (route) =>
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({message: 'Internal server error'}),
        }),
      );

      // Navigate to organization page
      await logoutPage.goto('/organization');
      await expect(logoutPage.getByTestId('user-menu-toggle')).toBeVisible();

      // Click user menu
      await logoutPage.getByTestId('user-menu-toggle').click();

      // Click logout
      await logoutPage.getByRole('menuitem', {name: 'Logout'}).click();

      // Should STILL redirect to signin page despite API error
      // The frontend handles this gracefully in a finally block
      await expect(logoutPage).toHaveURL(/\/signin/);

      // Should NOT show error modal
      await expect(logoutPage.getByText('Unable to log out')).not.toBeVisible();
    },
  );

  test(
    'clears session and prevents access to protected pages',
    {tag: '@superuser'},
    async ({logoutUser}) => {
      const {page: logoutPage, username: logoutUsername} =
        await logoutUser('logout-access');

      // Navigate to organization page
      await logoutPage.goto('/organization');
      await expect(logoutPage.getByTestId('user-menu-toggle')).toBeVisible();

      // Click user menu
      await logoutPage.getByTestId('user-menu-toggle').click();

      // Click logout
      await logoutPage.getByRole('menuitem', {name: 'Logout'}).click();

      // Should be on signin page
      await expect(logoutPage).toHaveURL(/\/signin/);

      // Verify login form is visible
      await expect(
        logoutPage.getByRole('textbox', {name: /username/i}),
      ).toBeVisible();

      // Try to navigate to a protected page (use the temp user's namespace)
      await logoutPage.goto(`/organization/${logoutUsername}`);

      // Should redirect back to signin (not authenticated)
      await expect(logoutPage).toHaveURL(/\/signin/);

      // Verify still on login page
      await expect(
        logoutPage.getByRole('textbox', {name: /username/i}),
      ).toBeVisible();
    },
  );

  test('logout menu item has danger styling', async ({authenticatedPage}) => {
    // This test doesn't perform logout, so it's safe to use the shared context
    await authenticatedPage.goto('/organization');
    await expect(
      authenticatedPage.getByTestId('user-menu-toggle'),
    ).toBeVisible();

    // Click user menu
    await authenticatedPage.getByTestId('user-menu-toggle').click();

    // Verify logout menu item exists and is visible
    const logoutMenuItem = authenticatedPage.getByRole('menuitem', {
      name: 'Logout',
    });
    await expect(logoutMenuItem).toBeVisible();

    // Verify logout menu item has danger styling
    // PatternFly applies pf-m-danger to the <li> wrapper element, not the button itself
    const listItem = authenticatedPage.locator('li.pf-m-danger', {
      has: logoutMenuItem,
    });
    await expect(listItem).toBeVisible();
  });
});
