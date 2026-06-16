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

    test('can create a Slack notification', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotifsl');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      await authenticatedPage
        .getByTestId('create-ns-notification-btn')
        .click();

      // Select event: Quota Warning
      await authenticatedPage
        .getByTestId('ns-notification-event-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-event-quota_warning').click();

      // Select method: Slack
      await authenticatedPage
        .getByTestId('ns-notification-method-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-method-slack').click();

      // Fill in Slack webhook URL
      await authenticatedPage
        .getByTestId('ns-notification-slack-url')
        .fill('https://hooks.slack.com/services/T00/B00/xxxx');

      // Fill in title
      await authenticatedPage
        .getByTestId('ns-notification-title')
        .fill('Slack Quota Warning');

      // Submit
      await authenticatedPage
        .getByTestId('ns-notification-submit-btn')
        .click();

      // Verify notification appears in list
      await expect(
        authenticatedPage.getByText('Slack Quota Warning'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Quota Warning'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Slack Notification'),
      ).toBeVisible();
    });

    test('can create a Quay notification with team recipient', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotifqn');
      const team = await api.team(org.name, 'notifteam');

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

      // Select method: Red Hat Quay Notification
      await authenticatedPage
        .getByTestId('ns-notification-method-dropdown')
        .click();
      await authenticatedPage
        .getByTestId('ns-method-quay_notification')
        .click();

      // Select team as recipient in entity search
      const entitySearch = authenticatedPage.getByTestId(
        'ns-notification-entity-search',
      );
      await entitySearch.fill(team.name);
      await authenticatedPage.getByText(team.name).click();

      // Fill in title
      await authenticatedPage
        .getByTestId('ns-notification-title')
        .fill('Quay Notification to Team');

      // Submit
      await authenticatedPage
        .getByTestId('ns-notification-submit-btn')
        .click();

      // Verify notification appears in list
      await expect(
        authenticatedPage.getByText('Quay Notification to Team'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Quota Error'),
      ).toBeVisible();
    });

    test('multiple notifications coexist in list', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotifmulti');

      // Create 3 notifications via API
      await api.namespaceNotification(
        org.name,
        'quota_warning',
        'webhook',
        {url: 'https://example.com/hook1'},
        {},
        'Webhook Warning',
      );
      await api.namespaceNotification(
        org.name,
        'quota_error',
        'email',
        {email: 'admin@example.com'},
        {},
        'Email Error',
      );
      await api.namespaceNotification(
        org.name,
        'quota_warning',
        'slack',
        {url: 'https://hooks.slack.com/services/T00/B00/xxxx'},
        {},
        'Slack Warning',
      );

      // Navigate to UI and verify all 3 visible
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      await expect(
        authenticatedPage.getByText('Webhook Warning'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Email Error'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Slack Warning'),
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

    test('both quota event types available in dropdown', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotifevt');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      await authenticatedPage
        .getByTestId('create-ns-notification-btn')
        .click();

      // Open event dropdown
      await authenticatedPage
        .getByTestId('ns-notification-event-dropdown')
        .click();

      // Both event types should be visible
      await expect(
        authenticatedPage.getByTestId('ns-event-quota_warning'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('ns-event-quota_error'),
      ).toBeVisible();

      // Repo events should NOT appear
      await expect(
        authenticatedPage.getByText('Push to Repository'),
      ).not.toBeVisible();
    });

    test('all four notification methods available, flowdock and hipchat excluded', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotifmeth');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      await authenticatedPage
        .getByTestId('create-ns-notification-btn')
        .click();

      // Select an event first to enable method dropdown
      await authenticatedPage
        .getByTestId('ns-notification-event-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-event-quota_warning').click();

      // Open method dropdown
      await authenticatedPage
        .getByTestId('ns-notification-method-dropdown')
        .click();

      // All four methods should be available
      await expect(
        authenticatedPage.getByTestId('ns-method-email'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('ns-method-slack'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('ns-method-webhook'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('ns-method-quay_notification'),
      ).toBeVisible();

      // Flowdock and HipChat should NOT be listed
      await expect(
        authenticatedPage.getByText('Flowdock'),
      ).not.toBeVisible();
      await expect(
        authenticatedPage.getByText('HipChat'),
      ).not.toBeVisible();
    });

    test('form validation — submit disabled without required fields', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotifval');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
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

    test('Quay notification — submit disabled without recipient', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotifqnval');
      const team = await api.team(org.name, 'valteam');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      await authenticatedPage
        .getByTestId('create-ns-notification-btn')
        .click();

      // Select event and Quay Notification method
      await authenticatedPage
        .getByTestId('ns-notification-event-dropdown')
        .click();
      await authenticatedPage.getByTestId('ns-event-quota_error').click();
      await authenticatedPage
        .getByTestId('ns-notification-method-dropdown')
        .click();
      await authenticatedPage
        .getByTestId('ns-method-quay_notification')
        .click();

      // Submit should be disabled (no recipient selected)
      await expect(
        authenticatedPage.getByTestId('ns-notification-submit-btn'),
      ).toBeDisabled();

      // Select team as recipient
      const entitySearch = authenticatedPage.getByTestId(
        'ns-notification-entity-search',
      );
      await entitySearch.fill(team.name);
      await authenticatedPage.getByText(team.name).click();

      // Submit should now be enabled
      await expect(
        authenticatedPage.getByTestId('ns-notification-submit-btn'),
      ).toBeEnabled();
    });
  },
);
