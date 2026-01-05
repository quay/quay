import {test as base, expect, uniqueName, mailpit} from '../../fixtures';
import {ApiClient} from '../../utils/api';

/**
 * Logout tests use unique temporary users to avoid session invalidation conflicts.
 *
 * Background: Quay's /api/v1/signout endpoint calls `invalidate_all_sessions(user)`
 * which invalidates ALL sessions for that user across all browser contexts.
 * This would cause parallel tests using the same user to fail.
 *
 * Solution: Create a unique user per test, use it, then delete it.
 */

interface LogoutTestFixtures {
  /** Fresh page with a unique temporary user - safe to logout */
  logoutPage: import('@playwright/test').Page;
  /** The unique username for cleanup reference */
  logoutUsername: string;
}

const test = base.extend<LogoutTestFixtures>({
  // eslint-disable-next-line no-empty-pattern
  logoutUsername: async ({}, use) => {
    // Generate unique username for this test
    const username = uniqueName('logout');
    await use(username);
  },

  logoutPage: async (
    {browser, superuserRequest, logoutUsername, quayConfig},
    use,
  ) => {
    const username = logoutUsername;
    const password = 'testpassword123';
    const email = `${username}@example.com`;
    const mailingEnabled = quayConfig?.features?.MAILING === true;

    // Create temporary user using superuser API
    const superApi = new ApiClient(superuserRequest);
    await superApi.createUser(username, password, email);

    // Create new context for this user
    const context = await browser.newContext();

    // Verify email if mailing is enabled
    if (mailingEnabled) {
      const confirmLink = await mailpit.waitForConfirmationLink(email);
      if (confirmLink) {
        const page = await context.newPage();
        await page.goto(confirmLink);
        await page.close();
      }
    }

    // Login as the temporary user
    const api = new ApiClient(context.request);
    await api.signIn(username, password);

    const page = await context.newPage();
    await use(page);

    // Cleanup
    await page.close();
    await context.close();

    // Delete the temporary user
    try {
      await superApi.deleteUser(username);
    } catch {
      // User may already be deleted or cleanup failed - that's ok
    }
  },
});

test.describe('Logout functionality', {tag: ['@auth', '@critical']}, () => {
  test('logs out successfully', async ({logoutPage}) => {
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

  test('redirects to signin even when logout API fails', async ({
    logoutPage,
  }) => {
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
  });

  test('clears session and prevents access to protected pages', async ({
    logoutPage,
    logoutUsername,
  }) => {
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
  });

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
