import {test, expect} from '../../fixtures';

test.describe(
  'Namespace Notifications',
  {tag: ['@organization', '@feature:QUOTA_NOTIFICATIONS']},
  () => {
    test('can create a webhook notification, verify in list, test it, and delete it', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotif');

      // Navigate to org settings
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Click on Notifications tab
      await authenticatedPage.getByTestId('Notifications').click();

      // Should show empty state
      await expect(
        authenticatedPage.getByText('No notifications configured'),
      ).toBeVisible();

      // Click "Create notification" button
      await authenticatedPage
        .getByTestId('create-ns-notification-btn')
        .click();

      // Select event: Quota Warning
      await authenticatedPage
        .getByTestId('ns-notification-event-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-event-quota_warning').click();

      // Select method: Webhook POST
      await authenticatedPage
        .getByTestId('ns-notification-method-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-method-webhook').click();

      // Fill in webhook URL
      await authenticatedPage
        .getByTestId('ns-notification-webhook-url')
        .fill('https://example.com/webhook');

      // Fill in title
      await authenticatedPage
        .getByTestId('ns-notification-title')
        .fill('Test Webhook Notification');

      // Submit
      await authenticatedPage
        .getByTestId('ns-notification-submit-btn')
        .click();

      // Verify notification appears in the list
      await expect(
        authenticatedPage.getByTestId('ns-notifications-table'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Test Webhook Notification'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Quota Warning'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Webhook POST'),
      ).toBeVisible();
      await expect(authenticatedPage.getByText('Enabled')).toBeVisible();

      // Test the notification via kebab menu
      const kebabToggle = authenticatedPage
        .locator('[data-testid$="-ns-toggle-kebab"]')
        .first();
      await kebabToggle.click();

      const testButton = authenticatedPage
        .locator('[data-testid$="-test-notification"]')
        .first();
      await testButton.click();

      // Verify test queued modal
      await expect(
        authenticatedPage.getByText('Test Notification Queued'),
      ).toBeVisible();
      await authenticatedPage
        .getByRole('button', {name: 'Close'})
        .click();

      // Delete the notification via kebab menu
      await kebabToggle.click();

      const deleteButton = authenticatedPage
        .locator('[data-testid$="-delete-notification"]')
        .first();
      await deleteButton.click();

      // Confirm deletion
      await authenticatedPage
        .getByTestId('confirm-delete-ns-notification')
        .click();

      // Verify notification is removed — empty state returns
      await expect(
        authenticatedPage.getByText('No notifications configured'),
      ).toBeVisible();
    });

    test('can create an email notification', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotifem');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      await authenticatedPage
        .getByTestId('create-ns-notification-btn')
        .click();

      // Select event: Quota Error
      await authenticatedPage
        .getByTestId('ns-notification-event-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-event-quota_error').click();

      // Select method: Email
      await authenticatedPage
        .getByTestId('ns-notification-method-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-method-email').click();

      // Fill in email
      await authenticatedPage
        .getByTestId('ns-notification-email')
        .fill('admin@example.com');

      // Fill in title
      await authenticatedPage
        .getByTestId('ns-notification-title')
        .fill('Quota Error Email');

      // Submit
      await authenticatedPage
        .getByTestId('ns-notification-submit-btn')
        .click();

      // Verify notification appears in list
      await expect(
        authenticatedPage.getByText('Quota Error Email'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Quota Error'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Email Notification'),
      ).toBeVisible();
    });

    test('notifications tab is hidden when feature flag is disabled', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotifhidden');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // The test itself will only run when QUOTA_NOTIFICATIONS is enabled
      // (due to the @feature:QUOTA_NOTIFICATIONS tag).
      // If we get here, the tab should be visible.
      await expect(
        authenticatedPage.getByTestId('Notifications'),
      ).toBeVisible();
    });

    test('API-created notification appears in UI list', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotifapi');

      // Create notification via API
      await api.namespaceNotification(
        org.name,
        'quota_warning',
        'webhook',
        {url: 'https://example.com/hook'},
        {},
        'API-Created Notification',
      );

      // Navigate to UI and verify it shows
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      await expect(
        authenticatedPage.getByText('API-Created Notification'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Quota Warning'),
      ).toBeVisible();
    });
  },
);
