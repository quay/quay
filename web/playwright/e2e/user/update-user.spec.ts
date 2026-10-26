import type {Page} from '@playwright/test';
import {test, expect} from '../../fixtures';
import {ApiClient} from '../../utils/api';

// A federated (LDAP) first login also gets the confirm_username prompt, which
// hides the metadata form until confirmed. Database users never get it.
async function confirmUsernameIfPrompted(page: Page) {
  const confirmHeading = page.getByRole('heading', {name: 'Confirm Username'});
  const metadataHeading = page.getByRole('heading', {
    name: /Tell us a bit more/i,
  });
  await expect(confirmHeading.or(metadataHeading)).toBeVisible();
  if (await confirmHeading.isVisible()) {
    await page.getByTestId('update-user-confirm-username-btn').click();
  }
}

test.describe('UpdateUser Page', {tag: ['@user', '@auth']}, () => {
  test(
    'redirects unauthenticated users to signin',
    {tag: '@critical'},
    async ({unauthenticatedPage}) => {
      await unauthenticatedPage.goto('/updateuser');

      // Component checks user.anonymous and redirects to /signin
      await expect(unauthenticatedPage).toHaveURL(/\/signin/);
    },
  );

  // TODO: Implement with real OAuth flow when OAuth testing is available
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  test.skip('does not redirect to signin after OAuth username confirmation', () => {});

  test.describe(
    'Profile metadata form',
    {tag: '@feature:USER_METADATA'},
    () => {
      test(
        'displays and submits profile form',
        {tag: '@superuser'},
        async ({browser, isolatedUser}) => {
          const {user} = await isolatedUser('metadata-submit');

          // Create new context for this user
          const context = await browser.newContext();

          // Login as the isolated user
          const api = new ApiClient(context.request);
          await api.signIn(user.username, user.password);

          const page = await context.newPage();
          await page.goto('/updateuser');
          await confirmUsernameIfPrompted(page);

          // If user has prompts, form should be visible
          await expect(
            page.getByRole('heading', {name: /Tell us a bit more/i}),
          ).toBeVisible();

          // Verify form fields are visible
          await expect(
            page.getByTestId('update-user-given-name'),
          ).toBeVisible();
          await expect(
            page.getByTestId('update-user-family-name'),
          ).toBeVisible();
          await expect(page.getByTestId('update-user-company')).toBeVisible();
          await expect(page.getByTestId('update-user-location')).toBeVisible();

          // Submit button should be disabled initially (no data entered)
          await expect(
            page.getByTestId('update-user-save-details-btn'),
          ).toBeDisabled();

          // Fill given name and submit
          await page
            .getByTestId('update-user-given-name')
            .fill('TestGivenName');
          await expect(
            page.getByTestId('update-user-save-details-btn'),
          ).toBeEnabled();
          await page.getByTestId('update-user-save-details-btn').click();

          // Should redirect away from updateuser
          await expect(page).not.toHaveURL(/\/updateuser/);

          await page.close();
          await context.close();
        },
      );

      test(
        'skips profile metadata with No thanks button',
        {tag: '@superuser'},
        async ({browser, isolatedUser}) => {
          const {user} = await isolatedUser('metadata-skip');

          // Create new context for this user
          const context = await browser.newContext();

          // Login as the isolated user
          const api = new ApiClient(context.request);
          await api.signIn(user.username, user.password);

          const page = await context.newPage();
          await page.goto('/updateuser');
          await confirmUsernameIfPrompted(page);

          // If user has prompts, form should be visible
          await expect(
            page.getByRole('heading', {name: /Tell us a bit more/i}),
          ).toBeVisible();

          // Click "No thanks" to skip
          await page.getByTestId('update-user-skip-btn').click();

          // Should redirect away from updateuser
          await expect(page).not.toHaveURL(/\/updateuser/);

          await page.close();
          await context.close();
        },
      );
    },
  );
});
