import {test, expect} from '../../fixtures';

test.describe(
  'User Namespace Notifications',
  {tag: ['@user', '@feature:QUOTA_NOTIFICATIONS']},
  () => {
    test('can create a webhook notification, verify in list, test it, and delete it', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto('/user/admin?tab=Settings');

      await authenticatedPage.getByTestId('Notifications').click();

      await expect(
        authenticatedPage.getByText('No notifications configured'),
      ).toBeVisible();

      await authenticatedPage
        .getByTestId('create-ns-notification-btn')
        .click();

      await authenticatedPage
        .getByTestId('ns-notification-event-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-event-quota_warning').click();

      await authenticatedPage
        .getByTestId('ns-notification-method-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-method-webhook').click();

      await authenticatedPage
        .getByTestId('ns-notification-webhook-url')
        .fill('https://example.com/user-webhook');

      await authenticatedPage
        .getByTestId('ns-notification-title')
        .fill('User Webhook Notification');

      await authenticatedPage
        .getByTestId('ns-notification-submit-btn')
        .click();

      await expect(
        authenticatedPage.getByTestId('ns-notifications-table'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('User Webhook Notification'),
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

      await authenticatedPage
        .getByTestId('confirm-delete-ns-notification')
        .click();

      await expect(
        authenticatedPage.getByText('No notifications configured'),
      ).toBeVisible();
    });

    test('can create an email notification', async ({authenticatedPage}) => {
      await authenticatedPage.goto('/user/admin?tab=Settings');
      await authenticatedPage.getByTestId('Notifications').click();

      await authenticatedPage
        .getByTestId('create-ns-notification-btn')
        .click();

      await authenticatedPage
        .getByTestId('ns-notification-event-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-event-quota_error').click();

      await authenticatedPage
        .getByTestId('ns-notification-method-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-method-email').click();

      await authenticatedPage
        .getByTestId('ns-notification-email')
        .fill('admin@example.com');

      await authenticatedPage
        .getByTestId('ns-notification-title')
        .fill('User Quota Error Email');

      await authenticatedPage
        .getByTestId('ns-notification-submit-btn')
        .click();

      await expect(
        authenticatedPage.getByText('User Quota Error Email'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Quota Error'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Email Notification'),
      ).toBeVisible();
    });

    test('API-created notification appears in UI list', async ({
      authenticatedPage,
      api,
    }) => {
      await api.userNamespaceNotification(
        'quota_warning',
        'webhook',
        {url: 'https://example.com/user-hook'},
        {},
        'API-Created User Notification',
      );

      await authenticatedPage.goto('/user/admin?tab=Settings');
      await authenticatedPage.getByTestId('Notifications').click();

      await expect(
        authenticatedPage.getByText('API-Created User Notification'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Quota Warning'),
      ).toBeVisible();
    });
  },
);
