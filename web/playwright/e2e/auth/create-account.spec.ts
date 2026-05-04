import {test as base, expect, uniqueName, mailpit} from '../../fixtures';
import {ApiClient} from '../../utils/api';
import {Page} from '@playwright/test';

/**
 * Create Account tests use unauthenticated browser contexts since they test
 * the account creation flow for anonymous visitors.
 *
 * Tests that create users must clean them up using superuser API.
 */

interface CreateAccountFixtures {
  /** Fresh unauthenticated page for create account tests */
  createAccountPage: Page;
  /** Helper to cleanup created users */
  cleanupUser: (username: string) => Promise<void>;
}

const test = base.extend<CreateAccountFixtures>({
  createAccountPage: async ({browser}, use) => {
    // Create a fresh browser context without any authentication
    const context = await browser.newContext();
    const page = await context.newPage();
    await use(page);
    await page.close();
    await context.close();
  },

  cleanupUser: async ({superuserRequest}, use) => {
    const superApi = new ApiClient(superuserRequest);
    const cleanup = async (username: string) => {
      try {
        await superApi.deleteUser(username);
      } catch {
        // User may already be deleted or cleanup failed - that's ok
      }
    };
    await use(cleanup);
  },
});

test.describe('Create Account Page', {tag: ['@auth']}, () => {
  test('form validation prevents invalid submissions', async ({
    createAccountPage,
  }) => {
    await createAccountPage.goto('/createaccount');

    // Verify page title (use heading role to avoid matching the button)
    await expect(
      createAccountPage.getByRole('heading', {name: 'Create Account'}),
    ).toBeVisible();

    // Verify form fields exist by checking the input elements
    await expect(
      createAccountPage.getByTestId('create-account-username'),
    ).toBeVisible();
    await expect(
      createAccountPage.getByTestId('create-account-email'),
    ).toBeVisible();
    await expect(
      createAccountPage.getByTestId('create-account-password'),
    ).toBeVisible();
    await expect(
      createAccountPage.getByTestId('create-account-confirm-password'),
    ).toBeVisible();

    // Submit button should be disabled on empty form
    const submitButton = createAccountPage.getByTestId('create-account-submit');
    await expect(submitButton).toBeDisabled();

    // Test invalid username (too short)
    const usernameInput = createAccountPage.getByTestId(
      'create-account-username',
    );
    await usernameInput.fill('ab');
    await expect(
      createAccountPage.getByText(
        'Username must be at least 3 characters and contain only letters',
      ),
    ).toBeVisible();

    // Test invalid email
    const emailInput = createAccountPage.getByTestId('create-account-email');
    await emailInput.fill('invalid-email');
    await expect(
      createAccountPage.getByText('Please enter a valid email address'),
    ).toBeVisible();

    // Test short password
    const passwordInput = createAccountPage.getByTestId(
      'create-account-password',
    );
    await passwordInput.fill('123');
    await expect(
      createAccountPage.getByText(
        'Password must be at least 8 characters long',
      ),
    ).toBeVisible();

    // Test password mismatch
    await passwordInput.fill('validpassword123');
    const confirmPasswordInput = createAccountPage.getByTestId(
      'create-account-confirm-password',
    );
    await confirmPasswordInput.fill('differentpassword');
    await expect(
      createAccountPage.getByText('Passwords must match'),
    ).toBeVisible();

    // Form should still be disabled with invalid inputs
    await expect(submitButton).toBeDisabled();

    // Now fix all validation errors
    await usernameInput.fill('validuser');
    await emailInput.fill('valid@example.com');
    await confirmPasswordInput.fill('validpassword123');

    // Submit button should now be enabled
    await expect(submitButton).toBeEnabled();
  });

  test(
    'creates account with valid inputs and redirects to organization',
    {tag: '@critical'},
    async ({createAccountPage, cleanupUser, quayConfig}) => {
      const username = uniqueName('newuser');
      const email = `${username}@example.com`;
      const password = 'validpassword123';
      const mailingEnabled = quayConfig?.features?.MAILING === true;

      await createAccountPage.goto('/createaccount');

      // Wait for the page to be fully loaded
      await expect(
        createAccountPage.getByRole('heading', {name: 'Create Account'}),
      ).toBeVisible();

      // Fill form with valid data
      await createAccountPage
        .getByTestId('create-account-username')
        .fill(username);
      await createAccountPage.getByTestId('create-account-email').fill(email);
      await createAccountPage
        .getByTestId('create-account-password')
        .fill(password);
      await createAccountPage
        .getByTestId('create-account-confirm-password')
        .fill(password);

      // Submit form - wait for button to be enabled after validation
      const submitButton = createAccountPage.getByTestId(
        'create-account-submit',
      );
      await expect(submitButton).toBeEnabled({timeout: 10000});
      await submitButton.click();

      // If FEATURE_MAILING is enabled, we need to confirm email first
      if (mailingEnabled) {
        // Wait for verification message to appear
        await expect(
          createAccountPage.getByTestId('awaiting-verification-alert'),
        ).toBeVisible({timeout: 10000});

        // Get confirmation link from email (searches by recipient address)
        const confirmLink = await mailpit.waitForConfirmationLink(email);
        expect(confirmLink).not.toBeNull();
        await createAccountPage.goto(confirmLink!);
      }

      // Should redirect to /organization or /updateuser after successful creation
      // (depends on whether user has prompts configured)
      // Use longer timeout for redirect to complete
      await expect(createAccountPage).toHaveURL(/\/(organization|updateuser)/, {
        timeout: 15000,
      });

      // Cleanup: delete the created user
      await cleanupUser(username);
    },
  );

  test('shows error for existing username', async ({
    createAccountPage,
    superuserRequest,
    cleanupUser,
  }) => {
    const username = uniqueName('existing');
    const email = `${username}@example.com`;
    const password = 'validpassword123';

    // Pre-create user via API
    const superApi = new ApiClient(superuserRequest);
    await superApi.createUser(username, password, email);

    await createAccountPage.goto('/createaccount');

    // Wait for the page to be fully loaded
    await expect(
      createAccountPage.getByRole('heading', {name: 'Create Account'}),
    ).toBeVisible();

    // Try to create the same user via UI
    await createAccountPage
      .getByTestId('create-account-username')
      .fill(username);
    await createAccountPage.getByTestId('create-account-email').fill(email);
    await createAccountPage
      .getByTestId('create-account-password')
      .fill(password);
    await createAccountPage
      .getByTestId('create-account-confirm-password')
      .fill(password);

    // Submit form
    const submitButton = createAccountPage.getByTestId('create-account-submit');
    await expect(submitButton).toBeEnabled({timeout: 10000});
    await submitButton.click();

    // Should show error message (actual message from API includes prefix)
    await expect(
      createAccountPage.getByText('The username already exists'),
    ).toBeVisible({timeout: 10000});

    // Should not redirect - still on create account page
    await expect(createAccountPage).toHaveURL(/\/createaccount/);

    // Cleanup
    await cleanupUser(username);
  });

  test('navigates to signin page via link', async ({createAccountPage}) => {
    await createAccountPage.goto('/createaccount');

    // Verify "Already have an account?" text exists
    await expect(
      createAccountPage.getByText('Already have an account?'),
    ).toBeVisible();

    // Click the "Sign in" link
    await createAccountPage.getByRole('link', {name: 'Sign in'}).click();

    // Should navigate to signin page
    await expect(createAccountPage).toHaveURL(/\/signin/);
  });

  test(
    'shows verification message when email verification required',
    {tag: '@feature:MAILING'},
    async ({createAccountPage, cleanupUser}) => {
      // This test only runs when FEATURE_MAILING is enabled
      // When enabled, new accounts require email verification
      const username = uniqueName('verifyuser');
      const email = `${username}@example.com`;
      const password = 'validpassword123';

      await createAccountPage.goto('/createaccount');

      // Fill form with valid data
      await createAccountPage
        .getByTestId('create-account-username')
        .fill(username);
      await createAccountPage.getByTestId('create-account-email').fill(email);
      await createAccountPage
        .getByTestId('create-account-password')
        .fill(password);
      await createAccountPage
        .getByTestId('create-account-confirm-password')
        .fill(password);

      // Submit form
      await createAccountPage.getByTestId('create-account-submit').click();

      // Should show verification message
      await expect(
        createAccountPage.getByTestId('awaiting-verification-alert'),
      ).toBeVisible();
      await expect(
        createAccountPage.getByText(
          'Thank you for registering! We have sent you an activation email.',
        ),
      ).toBeVisible();
      await expect(
        createAccountPage.getByText('verify your email address'),
      ).toBeVisible();

      // Form fields should be hidden
      await expect(
        createAccountPage.getByTestId('create-account-username'),
      ).not.toBeVisible();
      await expect(
        createAccountPage.getByTestId('create-account-email'),
      ).not.toBeVisible();
      await expect(
        createAccountPage.getByTestId('create-account-password'),
      ).not.toBeVisible();

      // Should still show sign in link
      await expect(
        createAccountPage.getByRole('link', {name: 'Sign in'}),
      ).toBeVisible();

      // Should not redirect
      await expect(createAccountPage).toHaveURL(/\/createaccount/);

      // Cleanup
      await cleanupUser(username);
    },
  );

  test(
    'redirects to updateuser when user has prompts',
    {tag: '@feature:QUOTA_MANAGEMENT'},
    async ({createAccountPage, cleanupUser, quayConfig}) => {
      // This test only runs when FEATURE_QUOTA_MANAGEMENT is enabled
      // When enabled, new users may have prompts (enter_name, enter_company)
      // that redirect them to /updateuser
      const username = uniqueName('promptuser');
      const email = `${username}@example.com`;
      const password = 'validpassword123';
      const mailingEnabled = quayConfig?.features?.MAILING === true;

      await createAccountPage.goto('/createaccount');

      // Fill form with valid data
      await createAccountPage
        .getByTestId('create-account-username')
        .fill(username);
      await createAccountPage.getByTestId('create-account-email').fill(email);
      await createAccountPage
        .getByTestId('create-account-password')
        .fill(password);
      await createAccountPage
        .getByTestId('create-account-confirm-password')
        .fill(password);

      // Submit form
      await createAccountPage.getByTestId('create-account-submit').click();

      // If FEATURE_MAILING is enabled, we need to confirm email first
      if (mailingEnabled) {
        // Wait for verification message to appear
        await expect(
          createAccountPage.getByTestId('awaiting-verification-alert'),
        ).toBeVisible({timeout: 10000});

        // Get confirmation link from email (searches by recipient address)
        const confirmLink = await mailpit.waitForConfirmationLink(email);
        expect(confirmLink).not.toBeNull();
        await createAccountPage.goto(confirmLink!);
      }

      // With QUOTA_MANAGEMENT enabled, user should have prompts
      // and be redirected to /updateuser
      await expect(createAccountPage).toHaveURL(/\/updateuser/, {
        timeout: 15000,
      });

      // Cleanup
      await cleanupUser(username);
    },
  );
});
