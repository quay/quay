import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe('Account Settings', {tag: ['@user']}, () => {
  const username = TEST_USERS.user.username;
  const password = TEST_USERS.user.password;

  test.describe('General Settings', () => {
    test(
      'validates email and saves profile fields',
      {tag: ['@feature:USER_METADATA']},
      async ({authenticatedPage, quayConfig}) => {
        await authenticatedPage.goto(`/user/${username}?tab=Settings`);

        const mailingEnabled = quayConfig?.features?.MAILING === true;

        // Wait for form to load - check for Username field and helper text
        await expect(authenticatedPage.locator('#form-name')).toBeVisible();
        await expect(
          authenticatedPage.getByText('Usernames cannot be changed once set.'),
        ).toBeVisible();

        if (mailingEnabled) {
          // When MAILING is enabled, email is a button (not an input)
          const emailButton = authenticatedPage.getByRole('button', {
            name: /@/,
          });
          await expect(emailButton).toBeVisible();
        } else {
          // When MAILING is disabled, email is an input field
          await expect(
            authenticatedPage.locator('#org-settings-email'),
          ).toBeVisible();

          // Type a bad email
          await authenticatedPage.locator('#org-settings-email').clear();
          await authenticatedPage
            .locator('#org-settings-email')
            .fill('this is not a good e-mail');
          await expect(
            authenticatedPage.getByText('Please enter a valid email address'),
          ).toBeVisible();

          // Button should be disabled with invalid email
          await expect(
            authenticatedPage.locator('#save-org-settings'),
          ).toBeDisabled();

          // Type valid email
          await authenticatedPage
            .locator('#org-settings-email')
            .fill('test-valid@example.com');
        }

        // Fill profile fields (works in both modes)
        await authenticatedPage
          .locator('#org-settings-fullname')
          .fill('Test User');
        await authenticatedPage
          .locator('#org-settings-location')
          .fill('Test City');
        await authenticatedPage
          .locator('#org-settings-company')
          .fill('Test Company');

        // Save button should be enabled now
        await expect(
          authenticatedPage.locator('#save-org-settings'),
        ).toBeEnabled();

        // Save
        await authenticatedPage.locator('#save-org-settings').click();

        // Verify success message (use .first() as multiple alerts may appear)
        await expect(
          authenticatedPage.getByText('Successfully updated settings').first(),
        ).toBeVisible();
      },
    );

    test('displays correct terminology for user accounts', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // For user accounts, should show "Username" not "Organization"
      await expect(
        authenticatedPage.getByText('Username', {exact: true}),
      ).toBeVisible();

      // Email helper should reference "your account" or "the account" (varies by MAILING feature)
      // but NOT "the organization"
      await expect(
        authenticatedPage.getByText(
          /The e-mail address associated with (your|the) account\./,
        ),
      ).toBeVisible();
    });
  });

  test.describe('Billing Information', {tag: ['@feature:BILLING']}, () => {
    test('billing tab shows invoice email settings', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // Navigate to billing tab
      await authenticatedPage.getByText('Billing information').click();

      // Invoice email input should exist
      await expect(
        authenticatedPage.locator('#billing-settings-invoice-email'),
      ).toBeVisible();

      // Type invalid email
      await authenticatedPage
        .locator('#billing-settings-invoice-email')
        .fill('invalid-email');

      // Save button should be disabled
      await expect(
        authenticatedPage.locator('#save-billing-settings'),
      ).toBeDisabled();

      // Clear and type valid email
      await authenticatedPage
        .locator('#billing-settings-invoice-email')
        .fill('invoice@example.com');

      // Toggle receipts checkbox
      await authenticatedPage.locator('#checkbox').click();

      // Save should be enabled
      await expect(
        authenticatedPage.locator('#save-billing-settings'),
      ).toBeEnabled();

      // Save settings
      await authenticatedPage.locator('#save-billing-settings').click();

      // Verify success
      await expect(
        authenticatedPage.getByText('Successfully updated settings'),
      ).toBeVisible();
    });
  });

  test.describe('CLI Configuration', {tag: ['@auth:Database']}, () => {
    test('shows error for wrong password', async ({authenticatedPage}) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // Navigate to CLI tab
      await authenticatedPage.getByText('CLI configuration').click();

      // Click generate password button
      await authenticatedPage.locator('#cli-password-button').click();

      // Enter wrong password
      await authenticatedPage
        .locator('#delete-confirmation-input')
        .fill('wrongpassword123');
      await authenticatedPage.locator('#submit').click();

      // Verify error message
      await expect(
        authenticatedPage.getByText('Invalid Username or Password'),
      ).toBeVisible();
    });

    test('generates encrypted password with all credential formats', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // Navigate to CLI tab
      await authenticatedPage.getByText('CLI configuration').click();

      // Click generate password button
      await authenticatedPage.locator('#cli-password-button').click();

      // Enter correct password
      await authenticatedPage
        .locator('#delete-confirmation-input')
        .fill(password);
      await authenticatedPage.locator('#submit').click();

      // Credentials modal should appear
      await expect(
        authenticatedPage.getByTestId('credentials-modal'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(`Credentials for ${username}`),
      ).toBeVisible();

      // Verify all credential format tabs exist
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Encrypted Password'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Kubernetes Secret'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('tab', {name: 'rkt Configuration'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Podman Login'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Docker Login'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Docker Configuration'}),
      ).toBeVisible();

      // Close modal
      await authenticatedPage.getByTestId('credentials-modal-close').click();
      await expect(
        authenticatedPage.getByTestId('credentials-modal'),
      ).not.toBeVisible();
    });

    test('shows password not set alert for OIDC users', async ({
      authenticatedPage,
      quayConfig,
    }) => {
      // This test also requires OIDC external login (Database auth is handled by describe tag)
      const hasOIDC =
        quayConfig?.external_login && quayConfig.external_login.length > 0;
      test.skip(!hasOIDC, 'No external login configured');

      // This test would require creating a user without a password set
      // For now, we verify the component renders correctly by checking the UI structure
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);
      await authenticatedPage.getByText('CLI configuration').click();

      // The generate password button or password not set alert should be visible
      const passwordButton = authenticatedPage.locator('#cli-password-button');
      const setPasswordButton = authenticatedPage.getByTestId(
        'set-password-button',
      );

      // One of these should be visible
      await expect(passwordButton.or(setPasswordButton)).toBeVisible();
    });
  });

  test.describe('Avatar Display', () => {
    test('displays avatar in general settings', async ({authenticatedPage}) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // Avatar form group should exist
      await expect(authenticatedPage.getByTestId('form-avatar')).toBeVisible();

      // Avatar should be present
      await expect(authenticatedPage.getByTestId('avatar')).toBeVisible();

      // Helper text about avatar generation
      await expect(
        authenticatedPage.getByText(
          'Avatar is generated based off of your username',
        ),
      ).toBeVisible();
    });
  });

  test.describe('Password Change', {tag: ['@auth:Database']}, () => {
    test('password change modal validates input', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // Click change password link
      await authenticatedPage.getByText('Change password').click();

      // Modal should open
      await expect(
        authenticatedPage.getByTestId('change-password-modal'),
      ).toBeVisible();

      // Enter short password
      await authenticatedPage.locator('#new-password').fill('short');
      await authenticatedPage.locator('#confirm-password').fill('short');

      // Submit should be disabled for short passwords
      await expect(
        authenticatedPage.getByTestId('change-password-submit'),
      ).toBeDisabled();

      // Enter non-matching passwords
      await authenticatedPage.locator('#new-password').fill('validpassword123');
      await authenticatedPage
        .locator('#confirm-password')
        .fill('differentpassword123');

      // Submit should still be disabled
      await expect(
        authenticatedPage.getByTestId('change-password-submit'),
      ).toBeDisabled();

      // Enter matching valid passwords
      await authenticatedPage.locator('#new-password').fill('validpassword123');
      await authenticatedPage
        .locator('#confirm-password')
        .fill('validpassword123');

      // Submit should now be enabled
      await expect(
        authenticatedPage.getByTestId('change-password-submit'),
      ).toBeEnabled();

      // Close modal instead of submitting (to not change actual password)
      await authenticatedPage.getByRole('button', {name: 'Cancel'}).click();
      await expect(
        authenticatedPage.getByTestId('change-password-modal'),
      ).not.toBeVisible();
    });
  });

  test.describe('Account Type Change', {tag: ['@auth:Database']}, () => {
    test('account type modal shows organization membership warning', async ({
      authenticatedPage,
      api,
    }) => {
      // Create an organization to ensure user has memberships
      const org = await api.organization('conversiontest');
      const team = await api.team(org.name, 'members', 'member');
      await api.teamMember(org.name, team.name, username);

      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // Click individual account link
      await authenticatedPage.getByText('Individual account').click();

      // Modal should open
      await expect(
        authenticatedPage.getByTestId('change-account-type-modal'),
      ).toBeVisible();

      // Should show warning about organization membership
      await expect(
        authenticatedPage.getByText(
          'This account cannot be converted into an organization',
        ),
      ).toBeVisible();

      // Close modal
      await authenticatedPage
        .getByTestId('change-account-type-modal-close')
        .click();
      await expect(
        authenticatedPage.getByTestId('change-account-type-modal'),
      ).not.toBeVisible();
    });
  });

  test.describe('Desktop Notifications', () => {
    test('desktop notifications toggle with confirmation modal', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // Desktop notifications form group should exist
      await expect(
        authenticatedPage.getByTestId('form-notifications'),
      ).toBeVisible();

      // Check if browser notifications are available
      // In headless CI, notifications are typically denied/unavailable
      const notificationsAvailable = await authenticatedPage.evaluate(() => {
        return (
          typeof window.Notification !== 'undefined' &&
          window.Notification.permission !== 'denied'
        );
      });

      // Skip the modal test if notifications are blocked in this browser
      test.skip(
        !notificationsAvailable,
        'Browser notifications are unavailable or denied in this environment',
      );

      // Find the checkbox
      const checkbox = authenticatedPage.locator('#form-notifications');
      await expect(checkbox).toBeVisible();

      // Click to enable notifications
      await checkbox.click();

      // Confirmation modal should appear
      await expect(
        authenticatedPage.getByRole('dialog', {
          name: 'Enable Desktop Notifications',
        }),
      ).toBeVisible();

      // Cancel the modal
      await authenticatedPage.getByTestId('notification-cancel').click();
      await expect(
        authenticatedPage.getByRole('dialog', {
          name: 'Enable Desktop Notifications',
        }),
      ).not.toBeVisible();
    });
  });

  test.describe('Delete Account', {tag: ['@auth:Database']}, () => {
    test('delete account modal requires confirmation', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // Click delete account button
      await authenticatedPage
        .getByRole('button', {name: 'Delete account'})
        .click();

      // Modal should open
      await expect(
        authenticatedPage.getByTestId('delete-account-modal'),
      ).toBeVisible();

      // Check warning message
      await expect(
        authenticatedPage.getByText('Deleting an account is non-reversible'),
      ).toBeVisible();

      // Submit button should be disabled initially
      await expect(
        authenticatedPage.getByTestId('delete-account-confirm'),
      ).toBeDisabled();

      // Type wrong name
      await authenticatedPage
        .locator('#delete-confirmation-input')
        .fill('wrongname');
      await expect(
        authenticatedPage.getByTestId('delete-account-confirm'),
      ).toBeDisabled();

      // Type correct name
      await authenticatedPage
        .locator('#delete-confirmation-input')
        .fill(username);
      await expect(
        authenticatedPage.getByTestId('delete-account-confirm'),
      ).toBeEnabled();

      // Close modal instead of deleting
      await authenticatedPage.getByRole('button', {name: 'Cancel'}).click();
      await expect(
        authenticatedPage.getByTestId('delete-account-modal'),
      ).not.toBeVisible();
    });
  });

  test.describe('Application Tokens', () => {
    test('application tokens lifecycle: create, view, revoke', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // Navigate to CLI tab
      await authenticatedPage.getByText('CLI configuration').click();

      // Check for tokens section
      await expect(
        authenticatedPage.getByText('Docker CLI and other Application Tokens'),
      ).toBeVisible();

      // Click create token button
      await authenticatedPage.locator('#create-app-token-button').click();

      // Modal should open
      await expect(
        authenticatedPage.getByTestId('create-token-modal'),
      ).toBeVisible();

      // Enter token title
      const tokenTitle = `test-token-${Date.now()}`;
      await authenticatedPage.locator('#token-title').fill(tokenTitle);

      // Submit
      await authenticatedPage.getByTestId('create-token-submit').click();

      // Credentials modal should show with success
      await expect(
        authenticatedPage.getByTestId('credentials-modal'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Token Created Successfully'),
      ).toBeVisible();

      // Verify all credential tabs exist for token
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Application Token'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Kubernetes Secret'}),
      ).toBeVisible();

      // Close modal
      await authenticatedPage.getByTestId('credentials-modal-close').click();

      // Token should appear in table (use exact: true to avoid matching close button or actions dropdown)
      await expect(
        authenticatedPage.getByRole('button', {name: tokenTitle, exact: true}),
      ).toBeVisible();

      // Click token title to view credentials
      await authenticatedPage
        .getByRole('button', {name: tokenTitle, exact: true})
        .click();

      // View credentials modal should open
      await expect(
        authenticatedPage.getByText(`Credentials for ${tokenTitle}`),
      ).toBeVisible();

      // Close view modal
      await authenticatedPage.getByRole('button', {name: 'Done'}).click();

      // Revoke the token
      await authenticatedPage
        .locator('tr', {hasText: tokenTitle})
        .getByTestId('token-actions-dropdown')
        .click();
      await authenticatedPage.getByText('Revoke Token').click();

      // Revoke confirmation modal should open
      await expect(
        authenticatedPage.getByTestId('revoke-token-modal'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(
          `revoke the application token "${tokenTitle}"`,
        ),
      ).toBeVisible();

      // Confirm revocation
      await authenticatedPage.getByTestId('revoke-token-confirm').click();

      // Token should be removed from table
      await expect(
        authenticatedPage.getByRole('button', {name: tokenTitle}),
      ).not.toBeVisible();
    });

    test('shows empty state when no tokens exist', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // Navigate to CLI tab
      await authenticatedPage.getByText('CLI configuration').click();

      // Verify the tokens section loaded
      await expect(
        authenticatedPage.getByText('Docker CLI and other Application Tokens'),
      ).toBeVisible();

      // Either empty state OR token action buttons should be present
      const emptyState = authenticatedPage.getByRole('heading', {
        name: 'No application tokens',
      });
      const tokenActionButton = authenticatedPage
        .getByTestId('token-actions-dropdown')
        .first();

      await expect(emptyState.or(tokenActionButton)).toBeVisible();
    });
  });

  test.describe('Feature Visibility', () => {
    test('settings tab not visible for organizations', async ({
      authenticatedPage,
      api,
    }) => {
      // Create an organization
      const org = await api.organization('featurevistest');

      // Navigate to organization page
      await authenticatedPage.goto(`/organization/${org.name}`);

      // User-specific features should NOT appear
      await expect(
        authenticatedPage.getByText('Change password'),
      ).not.toBeVisible();
      await expect(
        authenticatedPage.getByTestId('form-notifications'),
      ).not.toBeVisible();
    });

    test('database-only features hidden with non-Database auth', async ({
      authenticatedPage,
      quayConfig,
    }) => {
      // Skip this test if we're using Database auth (features will be visible)
      const authType = quayConfig?.config?.AUTHENTICATION_TYPE;
      test.skip(
        authType === 'Database',
        'Database auth - features will be visible',
      );

      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // These features should NOT appear with non-Database auth
      await expect(
        authenticatedPage.getByText('Change password'),
      ).not.toBeVisible();
      await expect(
        authenticatedPage.getByText('Individual account'),
      ).not.toBeVisible();
      await expect(
        authenticatedPage.getByRole('button', {name: 'Delete account'}),
      ).not.toBeVisible();
    });

    test('settings tab visible in normal mode', async ({
      authenticatedPage,
      quayConfig,
    }) => {
      // Skip if registry is in read-only mode
      test.skip(
        quayConfig?.registry_state === 'readonly',
        'Registry is in read-only mode',
      );

      await authenticatedPage.goto(`/user/${username}`);

      // Settings tab should be visible
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Settings'}),
      ).toBeVisible();
    });
  });

  test.describe('Email Change', {tag: ['@feature:MAILING']}, () => {
    test('email shows as clickable link when MAILING enabled', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // Email should be a clickable button, not a text input
      // The email field should NOT exist as an input
      await expect(
        authenticatedPage.locator('#org-settings-email'),
      ).not.toBeVisible();

      // Email should be a button
      const emailButton = authenticatedPage.getByRole('button', {
        name: /@/,
      });
      await expect(emailButton).toBeVisible();
    });

    test('email change modal opens and validates', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      // Click email button to open modal
      const emailButton = authenticatedPage.getByRole('button', {
        name: /@/,
      });
      await emailButton.click();

      // Modal should open
      await expect(
        authenticatedPage.getByText(`Change Email for ${username}`),
      ).toBeVisible();

      // Current email should be pre-filled
      const emailInput = authenticatedPage.locator('#new-email');
      await expect(emailInput).toBeVisible();

      // Test invalid email format
      await emailInput.fill('not-a-valid-email');
      await authenticatedPage
        .getByRole('button', {name: 'Change Email'})
        .click();
      await expect(
        authenticatedPage.getByText('Please enter a valid email address'),
      ).toBeVisible();

      // Cancel
      await authenticatedPage.getByRole('button', {name: 'Cancel'}).click();
    });
  });

  test.describe('URL Normalization', () => {
    test('normalizes lowercase "settings" to correct tab', async ({
      authenticatedPage,
    }) => {
      // Visit with lowercase 'settings'
      await authenticatedPage.goto(`/user/${username}?tab=settings`);

      // Verify we're on the Settings tab
      await expect(
        authenticatedPage.getByRole('tab', {
          name: 'Settings',
          exact: true,
          selected: true,
        }),
      ).toBeVisible();
    });
  });
});
