import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe(
  'User Namespace Notifications',
  {tag: ['@user', '@feature:QUOTA_NOTIFICATIONS']},
  () => {
    const username = TEST_USERS.user.username;

    test('can create a webhook notification, verify in list, test it, and delete it', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

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
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);
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

      await authenticatedPage.goto(`/user/${username}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      await expect(
        authenticatedPage.getByText('API-Created User Notification'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Quota Warning'),
      ).toBeVisible();
    });

    test('can create a Slack notification', async ({authenticatedPage}) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

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
      await authenticatedPage.getByTestId('ns-method-slack').click();

      await authenticatedPage
        .getByTestId('ns-notification-slack-url')
        .fill('https://hooks.slack.com/services/T00/B00/xxxx');

      await authenticatedPage
        .getByTestId('ns-notification-title')
        .fill('User Slack Notification');

      await authenticatedPage
        .getByTestId('ns-notification-submit-btn')
        .click();

      await expect(
        authenticatedPage.getByText('User Slack Notification'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Slack Notification'),
      ).toBeVisible();
    });

    test('multiple notifications coexist in user namespace list', async ({
      authenticatedPage,
      api,
    }) => {
      await api.userNamespaceNotification(
        'quota_warning',
        'webhook',
        {url: 'https://example.com/hook1'},
        {},
        'User Webhook 1',
      );
      await api.userNamespaceNotification(
        'quota_error',
        'email',
        {email: 'test@example.com'},
        {},
        'User Email 1',
      );

      await authenticatedPage.goto(`/user/${username}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      await expect(
        authenticatedPage.getByText('User Webhook 1'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('User Email 1'),
      ).toBeVisible();
    });

    test('Notifications tab is visible in user settings when feature flag enabled', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);

      await expect(
        authenticatedPage.getByTestId('Notifications'),
      ).toBeVisible();

      await authenticatedPage.getByTestId('Notifications').click();

      // Verify notification content area renders
      await expect(
        authenticatedPage.getByTestId('create-ns-notification-btn'),
      ).toBeVisible();
    });

    test('form validation — submit disabled without required fields', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      await authenticatedPage
        .getByTestId('create-ns-notification-btn')
        .click();

      // Submit should be disabled with no selections
      await expect(
        authenticatedPage.getByTestId('ns-notification-submit-btn'),
      ).toBeDisabled();

      // Select event only — still disabled
      await authenticatedPage
        .getByTestId('ns-notification-event-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-event-quota_warning').click();
      await expect(
        authenticatedPage.getByTestId('ns-notification-submit-btn'),
      ).toBeDisabled();

      // Select method — still disabled (no URL)
      await authenticatedPage
        .getByTestId('ns-notification-method-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-method-webhook').click();
      await expect(
        authenticatedPage.getByTestId('ns-notification-submit-btn'),
      ).toBeDisabled();

      // Fill webhook URL — now enabled
      await authenticatedPage
        .getByTestId('ns-notification-webhook-url')
        .fill('https://example.com/webhook');
      await expect(
        authenticatedPage.getByTestId('ns-notification-submit-btn'),
      ).toBeEnabled();
    });

    test('user namespace notifications are isolated from org notifications', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('userisolation');

      // Create a notification on the org namespace
      await api.namespaceNotification(
        org.name,
        'quota_warning',
        'webhook',
        {url: 'https://example.com/org-hook'},
        {},
        'Org Only Notification',
      );

      // Create a notification on the user namespace
      await api.userNamespaceNotification(
        'quota_error',
        'webhook',
        {url: 'https://example.com/user-hook'},
        {},
        'User Only Notification',
      );

      // Navigate to user settings — org notification should NOT appear
      await authenticatedPage.goto(`/user/${username}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();
      await expect(
        authenticatedPage.getByText('User Only Notification'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Org Only Notification'),
      ).not.toBeVisible();

      // Navigate to org settings — user notification should NOT appear
      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Settings`,
      );
      await authenticatedPage.getByTestId('Notifications').click();
      await expect(
        authenticatedPage.getByText('Org Only Notification'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('User Only Notification'),
      ).not.toBeVisible();
    });
  },
);
