/**
 * Create Account page tests
 *
 * Tests the account creation flow including form validation,
 * successful registration, error handling, and UI structure.
 */

import {test, expect, uniqueName, skipUnlessFeature} from '../../fixtures';
import {createUser, deleteUser} from '../../utils/api';

test.describe(
  'Create Account Page',
  {tag: ['@auth', '@create-account']},
  () => {
    test('form validation works correctly', async ({page}) => {
      await page.goto('/createaccount');

      // Submit button should be disabled with empty form
      await expect(
        page.getByRole('button', {name: 'Create Account'}),
      ).toBeDisabled();

      // Test invalid username (too short)
      await page.locator('#username').fill('ab');
      await expect(
        page.getByText('Username must be at least 3 characters'),
      ).toBeVisible();

      // Test invalid email
      await page.locator('#email').fill('invalid-email');
      await expect(
        page.getByText('Please enter a valid email address'),
      ).toBeVisible();

      // Test invalid password (too short)
      await page.locator('#password').fill('123');
      await expect(
        page.getByText('Password must be at least 8 characters'),
      ).toBeVisible();

      // Test password mismatch
      await page.locator('#password').fill('validpassword123');
      await page.locator('#confirm-password').fill('differentpassword');
      await expect(page.getByText('Passwords must match')).toBeVisible();

      // Form should still be disabled with validation errors
      await expect(
        page.getByRole('button', {name: 'Create Account'}),
      ).toBeDisabled();
    });

    test('successful account creation and login flow', async ({
      page,
      superuserRequest,
    }) => {
      const testUsername = uniqueName('newuser');
      const testEmail = `${testUsername}@example.com`;
      const testPassword = 'validpassword123';

      await page.goto('/createaccount');

      // Fill form with valid data
      await page.locator('#username').fill(testUsername);
      await page.locator('#email').fill(testEmail);
      await page.locator('#password').fill(testPassword);
      await page.locator('#confirm-password').fill(testPassword);

      // Form should be enabled with valid data
      await expect(
        page.getByRole('button', {name: 'Create Account'}),
      ).toBeEnabled();

      // Submit form
      await page.getByRole('button', {name: 'Create Account'}).click();

      // Should redirect to organization page after successful creation and auto-login
      // Note: If MAILING feature is enabled, this will show awaiting_verification instead
      await expect(page).toHaveURL(/\/(organization|updateuser)/, {
        timeout: 10000,
      });

      // Clean up: delete the test user
      try {
        await deleteUser(superuserRequest, testUsername);
      } catch {
        // User might already be deleted or not exist
      }
    });

    test('handles duplicate username error', async ({
      page,
      superuserRequest,
    }) => {
      // First create a user that we'll try to duplicate
      const existingUsername = uniqueName('existing');
      const existingEmail = `${existingUsername}@example.com`;

      // Create the existing user via API
      await createUser(
        page.request,
        existingUsername,
        'password123',
        existingEmail,
      );

      await page.goto('/createaccount');

      // Try to create account with same username
      await page.locator('#username').fill(existingUsername);
      await page.locator('#email').fill('different@example.com');
      await page.locator('#password').fill('validpassword123');
      await page.locator('#confirm-password').fill('validpassword123');

      // Submit form
      await page.getByRole('button', {name: 'Create Account'}).click();

      // Should show error message
      await expect(
        page.getByText(/username already exists|already taken/i),
      ).toBeVisible();

      // Should stay on create account page
      await expect(page).toHaveURL(/\/createaccount/);

      // Clean up
      try {
        await deleteUser(superuserRequest, existingUsername);
      } catch {
        // User might already be deleted
      }
    });

    test('navigation to signin page works', async ({page}) => {
      await page.goto('/createaccount');

      // Click "Sign in" link
      await page.getByRole('link', {name: 'Sign in'}).click();

      // Should navigate to signin page
      await expect(page).toHaveURL(/\/signin/);
    });

    test('displays proper form labels and structure', async ({page}) => {
      await page.goto('/createaccount');

      // Check page title
      await expect(
        page.getByRole('heading', {name: 'Create Account'}),
      ).toBeVisible();

      // Check form fields exist with proper labels
      await expect(page.getByText('Username')).toBeVisible();
      await expect(page.locator('#username')).toBeVisible();

      await expect(page.getByText('Email')).toBeVisible();
      await expect(page.locator('#email')).toBeVisible();

      await expect(page.getByText('Password').first()).toBeVisible();
      await expect(page.locator('#password')).toBeVisible();

      await expect(page.getByText('Confirm Password')).toBeVisible();
      await expect(page.locator('#confirm-password')).toBeVisible();

      // Check submit button
      await expect(
        page.getByRole('button', {name: 'Create Account'}),
      ).toBeVisible();

      // Check signin link
      await expect(page.getByText('Already have an account?')).toBeVisible();
      await expect(page.getByRole('link', {name: 'Sign in'})).toBeVisible();
    });

    test(
      'shows email verification message when MAILING feature is enabled',
      {
        tag: '@feature:MAILING',
      },
      async ({page}) => {
        // This test mocks the response because the awaiting_verification state
        // depends on backend MAILING feature configuration
        const testUsername = uniqueName('verifyuser');
        const testEmail = `${testUsername}@example.com`;

        // Mock the user creation endpoint to return awaiting_verification
        await page.route('**/api/v1/user/', async (route) => {
          if (route.request().method() === 'POST') {
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({awaiting_verification: true}),
            });
          } else {
            await route.continue();
          }
        });

        await page.goto('/createaccount');

        // Fill form with valid data
        await page.locator('#username').fill(testUsername);
        await page.locator('#email').fill(testEmail);
        await page.locator('#password').fill('validpassword123');
        await page.locator('#confirm-password').fill('validpassword123');

        // Submit form
        await page.getByRole('button', {name: 'Create Account'}).click();

        // Should show verification message
        await expect(
          page.getByTestId('awaiting-verification-alert'),
        ).toBeVisible();
        await expect(
          page.getByText('Thank you for registering!'),
        ).toBeVisible();
        await expect(page.getByText('verify your email address')).toBeVisible();

        // Form should be hidden
        await expect(page.locator('#username')).not.toBeVisible();
        await expect(page.locator('#email')).not.toBeVisible();
        await expect(page.locator('#password')).not.toBeVisible();

        // Should not redirect
        await expect(page).toHaveURL(/\/createaccount/);

        // Sign in link should still be visible
        await expect(page.getByRole('link', {name: 'Sign in'})).toBeVisible();
      },
    );

    test(
      'redirects to updateuser page when user has prompts',
      {
        tag: '@feature:QUOTA_MANAGEMENT',
      },
      async ({page, quayConfig, superuserRequest}) => {
        // Skip if QUOTA_MANAGEMENT is not enabled - prompts only appear with this feature
        test.skip(...skipUnlessFeature(quayConfig, 'QUOTA_MANAGEMENT'));

        const testUsername = uniqueName('promptuser');
        const testEmail = `${testUsername}@example.com`;
        const testPassword = 'validpassword123';

        await page.goto('/createaccount');

        // Fill form
        await page.locator('#username').fill(testUsername);
        await page.locator('#email').fill(testEmail);
        await page.locator('#password').fill(testPassword);
        await page.locator('#confirm-password').fill(testPassword);

        // Submit form
        await page.getByRole('button', {name: 'Create Account'}).click();

        // Should redirect to updateuser page for profile completion
        await expect(page).toHaveURL(/\/updateuser/, {timeout: 10000});

        // Clean up: delete the test user
        try {
          await deleteUser(superuserRequest, testUsername);
        } catch {
          // User might already be deleted or not exist
        }
      },
    );
  },
);
