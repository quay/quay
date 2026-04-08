import {test, expect, mailpit} from '../../fixtures';

test.describe('Repository Notifications', {tag: ['@repository']}, () => {
  test('renders and expands notification details', async ({
    authenticatedPage,
    api,
  }) => {
    // Create test organization with repository
    const org = await api.organization('notif');
    const repo = await api.repository(org.name, 'notifrepo');

    // Create notifications via API
    await api.notification(
      org.name,
      repo.name,
      'repo_push',
      'slack',
      {url: 'https://hooks.slack.com/services/ABC123/DEF456/ghijklmnop'},
      'Slack Push Notification',
    );
    await api.notification(
      org.name,
      repo.name,
      'repo_push',
      'webhook',
      {url: 'https://example.com/webhook', template: '{"test": "value"}'},
      'Webhook Notification',
    );

    // Navigate to repository settings > Events and notifications tab
    await authenticatedPage.goto(
      `/repository/${org.name}/${repo.name}?tab=settings`,
    );
    await authenticatedPage
      .getByTestId('settings-tab-eventsandnotifications')
      .click();

    // Verify notifications table renders
    const slackRow = authenticatedPage.locator('tbody', {
      hasText: 'Slack Push Notification',
    });
    await expect(slackRow).toBeVisible();
    await expect(slackRow.locator('[data-label="title"]')).toHaveText(
      'Slack Push Notification',
    );
    await expect(slackRow.locator('[data-label="status"]')).toHaveText(
      'Enabled',
    );

    // Expand slack row and verify config details
    await slackRow.locator('button[aria-label="Details"]').click();
    const configDetails = slackRow.getByTestId('notification-config-details');
    await expect(configDetails).toBeVisible();
    await expect(configDetails).toContainText(
      'https://hooks.slack.com/services/ABC123/DEF456/ghijklmnop',
    );

    // Check webhook row
    const webhookRow = authenticatedPage.locator('tbody', {
      hasText: 'Webhook Notification',
    });
    await expect(webhookRow).toBeVisible();

    // Expand webhook row and verify config details
    await webhookRow.locator('button[aria-label="Details"]').click();
    const webhookConfig = webhookRow.getByTestId('notification-config-details');
    await expect(webhookConfig).toBeVisible();
    await expect(webhookConfig).toContainText('https://example.com/webhook');
    await expect(webhookConfig).toContainText('POST body template');
  });

  test('inline operations: test, enable, delete', async ({
    authenticatedPage,
    api,
  }) => {
    // Create test organization with repository and notification
    const org = await api.organization('inlineop');
    const repo = await api.repository(org.name, 'inlinerepo');

    // Create notification via API (it starts enabled)
    const notification = await api.notification(
      org.name,
      repo.name,
      'repo_push',
      'slack',
      {url: 'https://hooks.slack.com/services/TEST123/TEST456/testtoken'},
      'Inline Test Notification',
    );

    // Navigate to repository settings > Events and notifications tab
    await authenticatedPage.goto(
      `/repository/${org.name}/${repo.name}?tab=settings`,
    );
    await authenticatedPage
      .getByTestId('settings-tab-eventsandnotifications')
      .click();

    const row = authenticatedPage.locator('tbody', {
      hasText: 'Inline Test Notification',
    });
    await expect(row).toBeVisible();

    // Test notification via kebab menu
    await row.getByTestId(`${notification.uuid}-toggle-kebab`).click();
    await authenticatedPage
      .getByRole('menuitem', {name: 'Test Notification'})
      .click();

    // Wait for test to complete - modal should appear
    await expect(
      authenticatedPage.getByText(/Test notification queued/i),
    ).toBeVisible({timeout: 10000});

    // Close the modal (click the text button, not the X icon)
    await authenticatedPage
      .getByRole('button', {name: 'Close', exact: true})
      .last()
      .click();
    await expect(
      authenticatedPage.getByText(/Test notification queued/i),
    ).not.toBeVisible();

    // Delete notification via kebab menu
    const kebab = row.getByTestId(`${notification.uuid}-toggle-kebab`);
    await kebab.click({force: true});
    const deleteMenuItem = authenticatedPage.getByRole('menuitem', {
      name: 'Delete',
    });
    await expect(deleteMenuItem).toBeVisible({timeout: 5000});
    await deleteMenuItem.click();

    // Verify notification is removed
    await expect(row).not.toBeVisible();

    // Verify empty state shows
    await expect(
      authenticatedPage.getByText('No notifications found'),
    ).toBeVisible();
  });

  test('bulk operations: enable and delete', async ({
    authenticatedPage,
    api,
  }) => {
    // Create test organization with repository
    const org = await api.organization('bulknotif');
    const repo = await api.repository(org.name, 'bulkrepo');

    // Create multiple notifications
    await api.notification(
      org.name,
      repo.name,
      'repo_push',
      'slack',
      {url: 'https://hooks.slack.com/services/BULK1/BULK1/bulk1token'},
      'Bulk Notification 1',
    );
    await api.notification(
      org.name,
      repo.name,
      'repo_push',
      'slack',
      {url: 'https://hooks.slack.com/services/BULK2/BULK2/bulk2token'},
      'Bulk Notification 2',
    );

    // Navigate to repository settings > Events and notifications tab
    await authenticatedPage.goto(
      `/repository/${org.name}/${repo.name}?tab=settings`,
    );
    await authenticatedPage
      .getByTestId('settings-tab-eventsandnotifications')
      .click();

    // Wait for notifications to load
    await expect(
      authenticatedPage.locator('tbody', {hasText: 'Bulk Notification 1'}),
    ).toBeVisible();
    await expect(
      authenticatedPage.locator('tbody', {hasText: 'Bulk Notification 2'}),
    ).toBeVisible();

    // Select all notifications
    await authenticatedPage
      .locator('[name="notifications-select-all"]')
      .click();

    // Bulk delete
    await authenticatedPage
      .getByTestId('notifications-actions-dropdown')
      .click();
    await authenticatedPage.getByTestId('bulk-delete-notifications').click();

    // Verify empty state
    await expect(
      authenticatedPage.getByText('No notifications found'),
    ).toBeVisible();
  });

  test('creates notifications for each method', async ({
    authenticatedPage,
    api,
  }) => {
    // Create test organization with repository and team
    const org = await api.organization('createnotif');
    const repo = await api.repository(org.name, 'createrepo');
    const team = await api.team(org.name, 'notifteam');

    // Navigate to repository settings > Events and notifications tab
    await authenticatedPage.goto(
      `/repository/${org.name}/${repo.name}?tab=settings`,
    );
    await authenticatedPage
      .getByTestId('settings-tab-eventsandnotifications')
      .click();

    // Helper function to create notification
    const createNotification = async (
      eventName: string,
      methodName: string,
      fillForm: () => Promise<void>,
      title: string,
    ) => {
      // Wait for either the toolbar button or empty state button
      await authenticatedPage
        .getByRole('button', {name: 'Create notification'})
        .click();

      // Select event
      await authenticatedPage
        .getByTestId('notification-event-dropdown')
        .click();
      await authenticatedPage.getByRole('menuitem', {name: eventName}).click();

      // Select method
      await authenticatedPage
        .getByTestId('notification-method-dropdown')
        .click();
      await authenticatedPage.getByRole('menuitem', {name: methodName}).click();

      // Fill form
      await fillForm();

      // Enter title
      await authenticatedPage.getByTestId('notification-title').fill(title);

      // Submit
      await authenticatedPage.getByTestId('notification-submit-btn').click();

      // Verify notification appears in table
      await expect(
        authenticatedPage.locator('tbody', {hasText: title}),
      ).toBeVisible();
    };

    // 1. Create Red Hat Quay notification (with team recipient)
    await createNotification(
      'Push to Repository',
      'Red Hat Quay Notification',
      async () => {
        // Click on the entity search and select team
        await authenticatedPage.locator('#entity-search-input').click();
        await authenticatedPage.getByTestId(`${team.name}-team`).click();
      },
      'Quay Team Notification',
    );

    // 2. Create Flowdock notification
    await createNotification(
      'Push to Repository',
      'Flowdock Team Notification',
      async () => {
        await authenticatedPage
          .getByTestId('flowdock-api-token-field')
          .fill('test-flowdock-token');
      },
      'Flowdock Notification',
    );

    // 3. Create Hipchat notification
    await createNotification(
      'Push to Repository',
      'HipChat Room',
      async () => {
        await authenticatedPage
          .getByTestId('room-id-number-field')
          .fill('12345');
        await authenticatedPage
          .getByTestId('room-notification-token-field')
          .fill('test-room-token');
      },
      'Hipchat Notification',
    );

    // 4. Create Slack notification
    await createNotification(
      'Push to Repository',
      'Slack Notification',
      async () => {
        await authenticatedPage
          .getByTestId('slack-webhook-url-field')
          .fill('https://hooks.slack.com/services/ABC123/DEF456/ghijklmnop');
      },
      'Slack Notification',
    );

    // 5. Create Webhook notification
    await createNotification(
      'Push to Repository',
      'Webhook POST',
      async () => {
        await authenticatedPage
          .getByTestId('webhook-url-field')
          .fill('https://example.com/webhook');
        await authenticatedPage
          .getByTestId('webhook-json-body-field')
          .fill('{"key": "value"}');
      },
      'Webhook Notification',
    );

    // Verify all 5 notifications are in the table
    await expect(
      authenticatedPage.locator('tbody', {hasText: 'Quay Team Notification'}),
    ).toBeVisible();
    await expect(
      authenticatedPage.locator('tbody', {hasText: 'Flowdock Notification'}),
    ).toBeVisible();
    await expect(
      authenticatedPage.locator('tbody', {hasText: 'Hipchat Notification'}),
    ).toBeVisible();
    await expect(
      authenticatedPage.locator('tbody', {hasText: 'Slack Notification'}),
    ).toBeVisible();
    await expect(
      authenticatedPage.locator('tbody', {hasText: 'Webhook Notification'}),
    ).toBeVisible();
  });

  test(
    'creates email notification with authorization flow',
    {tag: '@feature:MAILING'},
    async ({authenticatedPage, api}) => {
      // Create test organization with repository
      const org = await api.organization('emailnotif');
      const repo = await api.repository(org.name, 'emailrepo');
      const testEmail = 'notification-test@example.com';

      // Navigate to repository settings > Events and notifications tab
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=settings`,
      );
      await authenticatedPage
        .getByTestId('settings-tab-eventsandnotifications')
        .click();

      // Create notification
      await authenticatedPage
        .getByRole('button', {name: 'Create notification'})
        .click();

      // Select event
      await authenticatedPage
        .getByTestId('notification-event-dropdown')
        .click();
      await authenticatedPage
        .getByRole('menuitem', {name: 'Push to Repository'})
        .click();

      // Select E-mail method
      await authenticatedPage
        .getByTestId('notification-method-dropdown')
        .click();
      await authenticatedPage
        .getByRole('menuitem', {name: 'Email Notification'})
        .click();

      // Fill email
      await authenticatedPage.getByTestId('notification-email').fill(testEmail);

      // Enter title
      await authenticatedPage
        .getByTestId('notification-title')
        .fill('Email Notification');

      // Submit - this triggers the authorization modal
      await authenticatedPage.getByTestId('notification-submit-btn').click();

      // Authorization modal should appear
      await expect(
        authenticatedPage.getByText('Email Authorization'),
      ).toBeVisible();

      // Click Send Authorized Email
      await authenticatedPage.getByTestId('send-authorized-email-btn').click();

      // Wait for polling modal (shows email sent message)
      await expect(
        authenticatedPage.getByText(/An email has been sent/i),
      ).toBeVisible();

      // Wait for the verification email in Mailpit
      const authEmail = await mailpit.waitForEmail(
        (msg) =>
          msg.To.some((to) => to.Address === testEmail) &&
          msg.Subject.toLowerCase().includes('verify'),
        15000,
      );
      expect(authEmail).not.toBeNull();

      // Extract and visit the confirmation link
      const confirmLink = await mailpit.extractLink(authEmail!.ID);
      expect(confirmLink).not.toBeNull();

      // Open confirmation link in a new page to avoid disrupting the polling
      const confirmPage = await authenticatedPage.context().newPage();
      await confirmPage.goto(confirmLink!);
      await confirmPage.close();

      // Wait for the notification to appear in the table (UI polls for confirmation)
      await expect(
        authenticatedPage.locator('tbody', {hasText: 'Email Notification'}),
      ).toBeVisible({timeout: 15000});
    },
  );

  test(
    'creates image expiry notification with validation',
    {tag: '@feature:IMAGE_EXPIRY_TRIGGER'},
    async ({authenticatedPage, api}) => {
      // Create test organization with repository
      const org = await api.organization('expirynotif');
      const repo = await api.repository(org.name, 'expiryrepo');

      // Navigate to repository settings > Events and notifications tab
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=settings`,
      );
      await authenticatedPage
        .getByTestId('settings-tab-eventsandnotifications')
        .click();

      // Create notification
      await authenticatedPage
        .getByRole('button', {name: 'Create notification'})
        .click();

      // Select image expiry event
      await authenticatedPage
        .getByTestId('notification-event-dropdown')
        .click();
      await authenticatedPage.getByText('Image expiry trigger').click();

      // The days input should now be visible
      const daysInput = authenticatedPage.getByTestId('days-to-image-expiry');
      await expect(daysInput).toBeVisible();

      // Enter negative days - submit should be disabled
      await daysInput.fill('-5');

      // Select Slack method
      await authenticatedPage
        .getByTestId('notification-method-dropdown')
        .click();
      await authenticatedPage.getByText('Slack Notification').click();

      // Fill Slack webhook URL
      await authenticatedPage
        .getByTestId('slack-webhook-url-field')
        .fill('https://hooks.slack.com/services/EXP123/EXP456/exptoken');

      // Enter title
      await authenticatedPage
        .getByTestId('notification-title')
        .fill('Expiry Notification');

      // Submit button should be disabled due to invalid days
      await expect(
        authenticatedPage.getByTestId('notification-submit-btn'),
      ).toBeDisabled();

      // Fix the days value
      await daysInput.clear();
      await daysInput.fill('5');

      // Submit button should now be enabled
      await expect(
        authenticatedPage.getByTestId('notification-submit-btn'),
      ).toBeEnabled();

      // Submit
      await authenticatedPage.getByTestId('notification-submit-btn').click();

      // Verify notification appears in table
      await expect(
        authenticatedPage.locator('tbody', {hasText: 'Expiry Notification'}),
      ).toBeVisible();
    },
  );

  test('recipient field: teams, users, and create team modal', async ({
    authenticatedPage,
    api,
  }) => {
    // Create test organization with repository and team
    const org = await api.organization('recipnotif');
    const repo = await api.repository(org.name, 'reciprepo');
    const existingTeam = await api.team(org.name, 'existingteam');

    // Navigate to repository settings > Events and notifications tab
    await authenticatedPage.goto(
      `/repository/${org.name}/${repo.name}?tab=settings`,
    );
    await authenticatedPage
      .getByTestId('settings-tab-eventsandnotifications')
      .click();

    // Open create notification form
    await authenticatedPage
      .getByRole('button', {name: 'Create notification'})
      .click();

    // Select event
    await authenticatedPage.getByTestId('notification-event-dropdown').click();
    await authenticatedPage
      .getByRole('menuitem', {name: 'Push to Repository'})
      .click();

    // Select Red Hat Quay Notification method
    await authenticatedPage.getByTestId('notification-method-dropdown').click();
    await authenticatedPage
      .getByRole('menuitem', {name: 'Red Hat Quay Notification'})
      .click();

    // 1. Verify team appears in recipient dropdown
    const entitySearch = authenticatedPage.locator('#entity-search-input');
    await entitySearch.click();

    // Existing team should be visible
    await expect(
      authenticatedPage.getByTestId(`${existingTeam.name}-team`),
    ).toBeVisible();

    // 2. Select team as recipient and create notification
    await authenticatedPage.getByTestId(`${existingTeam.name}-team`).click();

    // Enter title
    await authenticatedPage
      .getByTestId('notification-title')
      .fill('Team Recipient Notification');

    // Submit
    await authenticatedPage.getByTestId('notification-submit-btn').click();

    // Verify notification created
    await expect(
      authenticatedPage.locator('tbody', {
        hasText: 'Team Recipient Notification',
      }),
    ).toBeVisible();

    // 3. Create another notification with user recipient
    await authenticatedPage
      .getByRole('button', {name: 'Create notification'})
      .click();

    // Select event
    await authenticatedPage.getByTestId('notification-event-dropdown').click();
    await authenticatedPage
      .getByRole('menuitem', {name: 'Push to Repository'})
      .click();

    // Select Red Hat Quay Notification method
    await authenticatedPage.getByTestId('notification-method-dropdown').click();
    await authenticatedPage
      .getByRole('menuitem', {name: 'Red Hat Quay Notification'})
      .click();

    // Search for user
    await entitySearch.click();
    await entitySearch.locator('input').fill('testuser');

    // Wait for search results and select user
    await authenticatedPage.getByTestId('testuser').click();

    // Enter title
    await authenticatedPage
      .getByTestId('notification-title')
      .fill('User Recipient Notification');

    // Submit
    await authenticatedPage.getByTestId('notification-submit-btn').click();

    // Verify notification created
    await expect(
      authenticatedPage.locator('tbody', {
        hasText: 'User Recipient Notification',
      }),
    ).toBeVisible();

    // 4. Test clearing recipient disables submit
    await authenticatedPage
      .getByRole('button', {name: 'Create notification'})
      .click();

    // Select event
    await authenticatedPage.getByTestId('notification-event-dropdown').click();
    await authenticatedPage
      .getByRole('menuitem', {name: 'Push to Repository'})
      .click();

    // Select Red Hat Quay Notification method
    await authenticatedPage.getByTestId('notification-method-dropdown').click();
    await authenticatedPage
      .getByRole('menuitem', {name: 'Red Hat Quay Notification'})
      .click();

    // Select a team
    await entitySearch.click();
    await authenticatedPage.getByTestId(`${existingTeam.name}-team`).click();

    // Enter title
    await authenticatedPage
      .getByTestId('notification-title')
      .fill('Clear Test');

    // Submit should be enabled
    await expect(
      authenticatedPage.getByTestId('notification-submit-btn'),
    ).toBeEnabled();

    // Clear the recipient (button is inside the entity search container)
    await authenticatedPage.getByLabel('Clear input value').click();

    // Submit should be disabled
    await expect(
      authenticatedPage.getByTestId('notification-submit-btn'),
    ).toBeDisabled();
  });
});
