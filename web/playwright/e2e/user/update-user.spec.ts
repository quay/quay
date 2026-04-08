import {test, expect, uniqueName, mailpit} from '../../fixtures';
import {ApiClient} from '../../utils/api';

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
      test('displays and submits profile form', async ({
        browser,
        superuserRequest,
        quayConfig,
      }) => {
        const username = uniqueName('updatetest');
        const password = 'testpassword123';
        const email = `${username}@example.com`;
        const mailingEnabled = quayConfig?.features?.MAILING === true;

        // Create temp user via superuser API
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

        // Login as the new user
        const api = new ApiClient(context.request);
        await api.signIn(username, password);

        const page = await context.newPage();
        await page.goto('/updateuser');

        // If user has prompts, form should be visible
        await expect(
          page.getByRole('heading', {name: /Tell us a bit more/i}),
        ).toBeVisible();

        // Verify form fields are visible
        await expect(page.getByTestId('update-user-given-name')).toBeVisible();
        await expect(page.getByTestId('update-user-family-name')).toBeVisible();
        await expect(page.getByTestId('update-user-company')).toBeVisible();
        await expect(page.getByTestId('update-user-location')).toBeVisible();

        // Submit button should be disabled initially (no data entered)
        await expect(
          page.getByTestId('update-user-save-details-btn'),
        ).toBeDisabled();

        // Fill given name and submit
        await page.getByTestId('update-user-given-name').fill('TestGivenName');
        await expect(
          page.getByTestId('update-user-save-details-btn'),
        ).toBeEnabled();
        await page.getByTestId('update-user-save-details-btn').click();

        // Should redirect away from updateuser
        await expect(page).not.toHaveURL(/\/updateuser/);

        await page.close();
        await context.close();

        // Cleanup
        try {
          await superApi.deleteUser(username);
        } catch {
          // User may already be deleted
        }
      });

      test('skips profile metadata with No thanks button', async ({
        browser,
        superuserRequest,
        quayConfig,
      }) => {
        const username = uniqueName('skiptest');
        const password = 'testpassword123';
        const email = `${username}@example.com`;
        const mailingEnabled = quayConfig?.features?.MAILING === true;

        // Create temp user via superuser API
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

        // Login as the new user
        const api = new ApiClient(context.request);
        await api.signIn(username, password);

        const page = await context.newPage();
        await page.goto('/updateuser');

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

        // Cleanup
        try {
          await superApi.deleteUser(username);
        } catch {
          // User may already be deleted
        }
      });
    },
  );
});
