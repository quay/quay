import {test, expect} from '../../fixtures';

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
});
