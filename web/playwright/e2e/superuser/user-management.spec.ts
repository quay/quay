/**
 * Superuser User Management E2E Tests
 *
 * Tests for superuser user management including:
 * - Create user
 * - Access control (own row, other superusers, regular users)
 * - Change email and password
 * - Toggle user status (enable/disable)
 * - Delete user
 * - Take ownership (convert user to org)
 * - Send recovery email
 * - Auth type visibility
 *
 * Requires SUPERUSERS_FULL_ACCESS feature to be enabled.
 *
 * Migrated from: web/cypress/e2e/superuser-user-management.cy.ts (29 tests consolidated to 10)
 */

import {
  test,
  expect,
  uniqueName,
  skipUnlessAuthType,
  skipUnlessFeature,
} from '../../fixtures';

test.describe(
  'Superuser User Management',
  {tag: ['@superuser', '@feature:SUPERUSERS_FULL_ACCESS']},
  () => {
    test('superuser can create user via UI', async ({
      superuserPage,
      superuserApi,
      quayConfig,
    }) => {
      // Skip if not using Database or AppToken auth (external auth can't create users)
      test.skip(...skipUnlessAuthType(quayConfig, 'Database', 'AppToken'));

      await superuserPage.goto('/organization');

      // Verify Create User button is visible
      await expect(
        superuserPage.getByTestId('create-user-button'),
      ).toBeVisible();
      await expect(
        superuserPage.getByTestId('create-user-button'),
      ).toContainText('Create User');

      // Open modal
      await superuserPage.getByTestId('create-user-button').click();
      await expect(superuserPage.getByRole('dialog')).toBeVisible();
      await expect(
        superuserPage.getByRole('heading', {name: 'Create New User'}),
      ).toBeVisible();

      // Fill form and create user
      const username = uniqueName('uiuser');
      const email = `${username}@example.com`;

      await superuserPage.getByTestId('username-input').fill(username);
      await superuserPage.getByTestId('email-input').fill(email);
      await superuserPage.getByTestId('create-user-submit').click();

      // Should show success message with temporary password
      await expect(
        superuserPage.getByText('User created successfully'),
      ).toBeVisible();

      // Close the success modal
      await superuserPage.getByRole('button', {name: 'Done'}).click();

      // Modal should close
      await expect(superuserPage.getByRole('dialog')).not.toBeVisible();

      // Cleanup: Delete the user we just created
      await superuserApi.raw.deleteUser(username);
    });

    test('user access control shows correct options based on user type', async ({
      superuserPage,
      superuserApi,
      quayConfig,
    }) => {
      // Create a test user (will be auto-cleaned)
      const testUser = await superuserApi.user('actestuser');

      await superuserPage.goto('/organization');

      // Use search to find the user (may be on different page due to pagination)
      await superuserPage
        .getByPlaceholder('Search by name...')
        .fill(testUser.username);
      await superuserPage.keyboard.press('Enter');

      // Wait for user to appear
      await expect(
        superuserPage.getByTestId(`${testUser.username}-options-toggle`),
      ).toBeVisible({timeout: 15000});

      // Regular user should have all management options
      await superuserPage
        .getByTestId(`${testUser.username}-options-toggle`)
        .click();

      // Verify expected menu items for regular users
      await expect(
        superuserPage.getByRole('menuitem', {name: 'Change E-mail Address'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('menuitem', {name: 'Change Password'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('menuitem', {name: 'Disable User'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('menuitem', {name: 'Delete User'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('menuitem', {name: 'Take Ownership'}),
      ).toBeVisible();

      // Configure Quota only visible if quota features are enabled
      if (
        quayConfig?.features?.QUOTA_MANAGEMENT ||
        quayConfig?.features?.EDIT_QUOTA
      ) {
        await expect(
          superuserPage.getByRole('menuitem', {name: 'Configure Quota'}),
        ).toBeVisible();
      }

      // Close menu
      await superuserPage.keyboard.press('Escape');
    });

    test('regular user cannot see superuser options', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto('/organization');

      // Create User button should NOT be visible for regular users
      await expect(
        authenticatedPage.getByTestId('create-user-button'),
      ).not.toBeVisible();

      // Settings column should not be visible
      await expect(
        authenticatedPage.getByRole('columnheader', {name: 'Settings'}),
      ).not.toBeVisible();
    });

    test('superuser can change user email', async ({
      superuserPage,
      superuserApi,
      quayConfig,
    }) => {
      // Skip if not Database auth (external auth manages email externally)
      test.skip(...skipUnlessAuthType(quayConfig, 'Database'));

      const testUser = await superuserApi.user('emailtest');

      await superuserPage.goto('/organization');

      // Use search to find the user
      await superuserPage
        .getByPlaceholder('Search by name...')
        .fill(testUser.username);
      await superuserPage.keyboard.press('Enter');

      // Wait for and click options toggle
      await superuserPage
        .getByTestId(`${testUser.username}-options-toggle`)
        .click();
      await superuserPage
        .getByRole('menuitem', {name: 'Change E-mail Address'})
        .click();

      // Verify modal opens
      await expect(superuserPage.getByRole('dialog')).toBeVisible();
      await expect(
        superuserPage.getByRole('heading', {
          name: `Change Email for ${testUser.username}`,
        }),
      ).toBeVisible();

      // Enter new email and submit
      const newEmail = `${testUser.username}-new@example.com`;
      await superuserPage
        .getByRole('dialog')
        .locator('input[type="email"]')
        .fill(newEmail);
      await superuserPage
        .getByRole('dialog')
        .getByRole('button', {name: 'Change Email'})
        .click();

      // Modal should close on success
      await expect(superuserPage.getByRole('dialog')).not.toBeVisible();
    });

    test('superuser can change user password', async ({
      superuserPage,
      superuserApi,
      quayConfig,
    }) => {
      // Skip if not Database auth
      test.skip(...skipUnlessAuthType(quayConfig, 'Database'));

      const testUser = await superuserApi.user('pwdtest');

      await superuserPage.goto('/organization');

      // Use search to find the user
      await superuserPage
        .getByPlaceholder('Search by name...')
        .fill(testUser.username);
      await superuserPage.keyboard.press('Enter');

      await superuserPage
        .getByTestId(`${testUser.username}-options-toggle`)
        .click();
      await superuserPage
        .getByRole('menuitem', {name: 'Change Password'})
        .click();

      // Verify modal opens
      await expect(superuserPage.getByRole('dialog')).toBeVisible();
      await expect(
        superuserPage.getByRole('heading', {
          name: `Change Password for ${testUser.username}`,
        }),
      ).toBeVisible();

      // Enter new password and submit
      await superuserPage
        .getByRole('dialog')
        .locator('input[type="password"]')
        .fill('newpassword123');
      await superuserPage
        .getByRole('dialog')
        .getByRole('button', {name: 'Change Password'})
        .click();

      // Modal should close on success
      await expect(superuserPage.getByRole('dialog')).not.toBeVisible();
    });

    test('superuser can toggle user status (disable/enable)', async ({
      superuserPage,
      superuserApi,
    }) => {
      const testUser = await superuserApi.user('toggletest');

      await superuserPage.goto('/organization');

      // Use search to find the user
      await superuserPage
        .getByPlaceholder('Search by name...')
        .fill(testUser.username);
      await superuserPage.keyboard.press('Enter');

      // Disable the user
      await superuserPage
        .getByTestId(`${testUser.username}-options-toggle`)
        .click();
      await superuserPage.getByRole('menuitem', {name: 'Disable User'}).click();

      // Confirm in dialog
      await expect(superuserPage.getByRole('dialog')).toBeVisible();
      await superuserPage
        .getByRole('dialog')
        .getByRole('button', {name: 'Disable User'})
        .click();
      await expect(superuserPage.getByRole('dialog')).not.toBeVisible();

      // Wait for page to update, then verify Enable User option appears
      await superuserPage.reload();

      // Re-search for user after reload
      await superuserPage
        .getByPlaceholder('Search by name...')
        .fill(testUser.username);
      await superuserPage.keyboard.press('Enter');

      await superuserPage
        .getByTestId(`${testUser.username}-options-toggle`)
        .click();
      await expect(
        superuserPage.getByRole('menuitem', {name: 'Enable User'}),
      ).toBeVisible();

      // Re-enable the user
      await superuserPage.getByRole('menuitem', {name: 'Enable User'}).click();

      // Confirm in dialog
      await expect(superuserPage.getByRole('dialog')).toBeVisible();
      await superuserPage
        .getByRole('dialog')
        .getByRole('button', {name: 'Enable User'})
        .click();
      await expect(superuserPage.getByRole('dialog')).not.toBeVisible();
    });

    test('superuser can delete user', async ({superuserPage, superuserApi}) => {
      // Create user via API (don't use auto-cleanup since we're deleting via UI)
      const username = uniqueName('deltest');
      const email = `${username}@example.com`;
      await superuserApi.raw.createUserAsSuperuser(username, email);

      await superuserPage.goto('/organization');

      // Use search to find the user
      await superuserPage.getByPlaceholder('Search by name...').fill(username);
      await superuserPage.keyboard.press('Enter');

      // Wait for user to appear
      await expect(
        superuserPage.getByTestId(`${username}-options-toggle`),
      ).toBeVisible({timeout: 15000});

      // Delete the user
      await superuserPage.getByTestId(`${username}-options-toggle`).click();
      await superuserPage.getByRole('menuitem', {name: 'Delete User'}).click();

      // Verify confirmation modal
      await expect(superuserPage.getByRole('dialog')).toBeVisible();
      await expect(
        superuserPage.getByText('permanently deleted'),
      ).toBeVisible();

      // Confirm deletion
      await superuserPage
        .getByRole('dialog')
        .getByRole('button', {name: 'Delete User'})
        .click();

      // Modal should close
      await expect(superuserPage.getByRole('dialog')).not.toBeVisible();

      // Reload and verify user is gone
      await superuserPage.reload();
      await expect(
        superuserPage.getByTestId(`${username}-options-toggle`),
      ).not.toBeVisible();
    });

    test('superuser can take ownership of user (converts to org)', async ({
      superuserPage,
      superuserApi,
    }) => {
      // Create user for take ownership test
      const username = uniqueName('takeown');
      const email = `${username}@example.com`;
      await superuserApi.raw.createUserAsSuperuser(username, email);

      await superuserPage.goto('/organization');

      // Use search to find the user
      await superuserPage.getByPlaceholder('Search by name...').fill(username);
      await superuserPage.keyboard.press('Enter');

      // Wait for user to appear
      await expect(
        superuserPage.getByTestId(`${username}-options-toggle`),
      ).toBeVisible({timeout: 15000});

      // Take ownership
      await superuserPage.getByTestId(`${username}-options-toggle`).click();
      await superuserPage
        .getByRole('menuitem', {name: 'Take Ownership'})
        .click();

      // Verify modal opens with conversion warning
      await expect(superuserPage.getByRole('dialog')).toBeVisible();
      await expect(
        superuserPage.getByText(
          'convert the user namespace into an organization',
        ),
      ).toBeVisible();

      // Confirm take ownership
      await superuserPage
        .getByRole('dialog')
        .getByRole('button', {name: 'Take Ownership'})
        .click();

      // Should navigate to the organization page
      await superuserPage.waitForURL(`**/organization/${username}**`);
      await expect(superuserPage).toHaveURL(
        new RegExp(`/organization/${username}`),
      );

      // Cleanup: Delete the org that was created from the user
      await superuserApi.raw.deleteOrganization(username);
    });

    test('fresh login error handling shows error for wrong password', async ({
      superuserPage,
      superuserApi,
    }) => {
      // This test uses page.route() to mock the fresh_login_required error
      // This is the only acceptable mock per MIGRATION.md

      // Set up routes BEFORE any navigation to ensure they're applied
      // Mock fresh_login_required on first change email attempt
      let putCallCount = 0;
      await superuserPage.route(
        '**/api/v1/superuser/users/*',
        async (route, request) => {
          if (request.method() === 'PUT') {
            putCallCount++;
            if (putCallCount === 1) {
              await route.fulfill({
                status: 401,
                contentType: 'application/json',
                body: JSON.stringify({
                  title: 'fresh_login_required',
                  error_message: 'Fresh login required',
                }),
              });
            } else {
              await route.continue();
            }
          } else {
            await route.continue();
          }
        },
      );

      // Mock failed password verification
      await superuserPage.route('**/api/v1/signin/verify', async (route) => {
        await route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({
            message: 'Invalid Username or Password',
            invalidCredentials: true,
          }),
        });
      });

      // Create test user
      const testUser = await superuserApi.user('freshlogin');

      await superuserPage.goto('/organization');

      // Use search to find the user
      await superuserPage
        .getByPlaceholder('Search by name...')
        .fill(testUser.username);
      await superuserPage.keyboard.press('Enter');

      // Wait for user to appear
      await expect(
        superuserPage.getByTestId(`${testUser.username}-options-toggle`),
      ).toBeVisible({timeout: 15000});

      // Trigger change email
      await superuserPage
        .getByTestId(`${testUser.username}-options-toggle`)
        .click();
      await superuserPage
        .getByRole('menuitem', {name: 'Change E-mail Address'})
        .click();

      // Fill and submit email change
      await superuserPage
        .getByRole('dialog')
        .locator('input[type="email"]')
        .fill('newemail@example.com');
      await superuserPage
        .getByRole('dialog')
        .getByRole('button', {name: 'Change Email'})
        .click();

      // Should show fresh login modal (wait longer for the modal to appear)
      await expect(
        superuserPage.getByText('Please Verify', {exact: true}),
      ).toBeVisible({timeout: 10000});

      // Enter wrong password and verify
      await superuserPage.locator('#fresh-password').fill('wrongpassword');
      await superuserPage.locator('#fresh-password').press('Enter');

      // Should show error after failed verification
      await expect(
        superuserPage.getByText('Invalid verification credentials'),
      ).toBeVisible({timeout: 10000});
    });

    test('superuser can send recovery email when MAILING enabled', async ({
      superuserPage,
      superuserApi,
      quayConfig,
    }) => {
      // Skip if MAILING feature is not enabled or not Database auth
      test.skip(...skipUnlessFeature(quayConfig, 'MAILING'));
      test.skip(...skipUnlessAuthType(quayConfig, 'Database'));

      const testUser = await superuserApi.user('recoverytest');

      await superuserPage.goto('/organization');

      // Use search to find the user
      await superuserPage
        .getByPlaceholder('Search by name...')
        .fill(testUser.username);
      await superuserPage.keyboard.press('Enter');

      // Open options menu
      await superuserPage
        .getByTestId(`${testUser.username}-options-toggle`)
        .click();

      // Verify Send Recovery E-mail option is visible
      await expect(
        superuserPage.getByRole('menuitem', {name: 'Send Recovery E-mail'}),
      ).toBeVisible();

      // Click to send recovery email
      await superuserPage
        .getByRole('menuitem', {name: 'Send Recovery E-mail'})
        .click();

      // Verify confirmation modal
      await expect(superuserPage.getByRole('dialog')).toBeVisible();
      await expect(
        superuserPage.getByText(
          'Are you sure you want to send a recovery email',
        ),
      ).toBeVisible();

      // Confirm send
      await superuserPage
        .getByRole('dialog')
        .getByRole('button', {name: 'Send Recovery Email'})
        .click();

      // Should show success message
      await expect(
        superuserPage.getByText(/recovery email has been sent/),
      ).toBeVisible();
    });

    test('auth type visibility shows correct UI elements', async ({
      superuserPage,
      quayConfig,
    }) => {
      const authType = quayConfig?.config?.AUTHENTICATION_TYPE as string;

      await superuserPage.goto('/organization');

      if (authType === 'Database' || authType === 'AppToken') {
        // Database/AppToken: Create User button should be visible
        await expect(
          superuserPage.getByTestId('create-user-button'),
        ).toBeVisible();
        // External auth alert should NOT be visible
        await expect(
          superuserPage.getByTestId('external-auth-alert'),
        ).not.toBeVisible();
      } else if (authType === 'LDAP' || authType === 'OIDC') {
        // LDAP/OIDC: Create User button should NOT be visible
        await expect(
          superuserPage.getByTestId('create-user-button'),
        ).not.toBeVisible();
        // External auth alert should be visible
        await expect(
          superuserPage.getByTestId('external-auth-alert'),
        ).toBeVisible();
        await expect(
          superuserPage.getByText(
            'Red Hat Quay is configured to use external authentication',
          ),
        ).toBeVisible();
      }
    });
  },
);
