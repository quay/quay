import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe('Organization Settings', {tag: ['@organization']}, () => {
  test.describe('General Settings', {tag: ['@feature:USER_METADATA']}, () => {
    test('validates email and saves settings', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('settingstest');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Wait for the form to load
      const emailInput = authenticatedPage.locator('#org-settings-email');
      await expect(emailInput).toBeVisible();

      // Type a bad email
      await emailInput.clear();
      await emailInput.fill('this is not a good e-mail');
      await expect(
        authenticatedPage.getByText('Please enter a valid email address'),
      ).toBeVisible();

      // Leave empty (email field is not required, so no error should appear)
      await emailInput.clear();

      // Check save button is disabled when form is not dirty or invalid
      const saveButton = authenticatedPage.locator('#save-org-settings');
      await expect(saveButton).toBeDisabled();

      // Type a good email and save
      await emailInput.fill('good-email@redhat.com');
      await expect(saveButton).toBeEnabled();
      await saveButton.click();

      // Verify success message
      await expect(
        authenticatedPage.getByText('Successfully updated settings').first(),
      ).toBeVisible();

      // Refresh page and check if email is saved
      await authenticatedPage.reload();
      await expect(emailInput).toHaveValue('good-email@redhat.com');
    });
  });

  test.describe('Billing Information', {tag: ['@feature:BILLING']}, () => {
    test('validates billing email and receipt settings', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('billingtest');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Navigate to billing tab
      await authenticatedPage.getByText('Billing information').click();

      // Wait for billing form to load
      const invoiceEmailInput = authenticatedPage.locator(
        '#billing-settings-invoice-email',
      );
      await expect(invoiceEmailInput).toBeVisible();

      // Type a bad email
      await invoiceEmailInput.clear();
      await invoiceEmailInput.fill('this is not a good e-mail');

      // Check save button is disabled with invalid email
      const saveButton = authenticatedPage.locator('#save-billing-settings');
      await expect(saveButton).toBeDisabled();

      // Clear and type a good email
      await invoiceEmailInput.clear();
      await invoiceEmailInput.fill('invoice-email@redhat.com');

      // Toggle save receipts checkbox
      const checkbox = authenticatedPage.locator('#checkbox');
      await expect(checkbox).not.toBeChecked();
      await checkbox.click();

      // Save
      await expect(saveButton).toBeEnabled();
      await saveButton.click();

      // Verify success message
      await expect(
        authenticatedPage.getByText('Successfully updated settings').first(),
      ).toBeVisible();

      // Refresh page, navigate to billing tab and check if settings are saved
      await authenticatedPage.reload();
      await authenticatedPage.getByText('Billing information').click();
      await expect(invoiceEmailInput).toHaveValue('invoice-email@redhat.com');
      await expect(checkbox).toBeChecked();
    });
  });

  test('CLI token tab not visible for organizations', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('clitest');

    await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

    // Ensure settings page is loaded by checking for the email input
    await expect(
      authenticatedPage.locator('#org-settings-email'),
    ).toBeVisible();

    // Ensure CLI configuration tab is not visible for organizations
    await expect(
      authenticatedPage.getByRole('tab', {name: 'CLI configuration'}),
    ).not.toBeVisible();
  });

  test.describe(
    'User Namespace Settings: Auto-Prune Policies tab',
    {tag: ['@feature:AUTO_PRUNE', '@user']},
    () => {
      test('shows Auto-Prune tab and hides org-only tabs for user namespace', async ({
        authenticatedPage,
      }) => {
        const username = TEST_USERS.user.username;

        // Regression: React Query v4 keeps disabled queries in isLoading=true.
        // useOrgMirrorExists and useFetchProxyCacheConfig are disabled for user
        // orgs (enabled = flag && !isUserOrg), but isLoading stays true when
        // no cached data exists, blocking mutualExclusionLoaded and hiding the
        // Auto-Prune tab. Enable both flags to cover both short-circuit paths.
        await authenticatedPage.route('**/config', async (route) => {
          const response = await route.fetch();
          const body = await response.json();
          Object.assign(body.features, {
            AUTO_PRUNE: true,
            PROXY_CACHE: true,
            ORG_MIRROR: true,
            IMMUTABLE_TAGS: false,
          });
          await route.fulfill({response, body: JSON.stringify(body)});
        });

        await authenticatedPage.goto(`/user/${username}?tab=Settings`);
        await expect(authenticatedPage.locator('#form-name')).toBeVisible();

        // Auto-Prune tab must be visible and navigable
        const autoPruneTab = authenticatedPage.getByTestId(
          'Auto-Prune Policies',
        );
        await expect(autoPruneTab).toBeVisible();
        await autoPruneTab.click();
        await expect(
          authenticatedPage.getByRole('heading', {
            name: 'Auto-Pruning Policies',
            level: 2,
          }),
        ).toBeVisible();

        // CLI configuration is user-namespace only
        await expect(
          authenticatedPage.getByTestId('CLI configuration'),
        ).toBeVisible();

        // Org-only tabs must not render in user namespace
        await expect(
          authenticatedPage.getByTestId('Proxy Cache'),
        ).not.toBeAttached();
        await expect(
          authenticatedPage.getByTestId('Organization state'),
        ).not.toBeAttached();
      });
    },
  );

  test.describe(
    'Duplicate Email on Update',
    {tag: ['@feature:MAILING']},
    () => {
      test('rejects updating organization email to one already in use (OCP-73836)', async ({
        authenticatedPage,
        api,
      }) => {
        const org1 = await api.organization('emaildup');
        const org2 = await api.organization('emaildup');

        await authenticatedPage.goto(`/organization/${org2.name}?tab=Settings`);

        const emailInput = authenticatedPage.locator('#org-settings-email');
        await expect(emailInput).toBeVisible();

        await emailInput.clear();
        await emailInput.fill(org1.email);

        const saveButton = authenticatedPage.locator('#save-org-settings');
        await expect(saveButton).toBeEnabled();
        await saveButton.click();

        await expect(
          authenticatedPage.getByText('E-mail address already used').first(),
        ).toBeVisible();
      });
    },
  );
});
