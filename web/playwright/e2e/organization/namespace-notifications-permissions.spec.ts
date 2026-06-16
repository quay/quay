import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe(
  'Namespace Notifications — Permissions',
  {tag: ['@organization', '@feature:QUOTA_NOTIFICATIONS']},
  () => {
    test('org admin can create and delete notifications', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotifperm');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      // Create a webhook notification
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
        .fill('https://example.com/webhook');
      await authenticatedPage
        .getByTestId('ns-notification-title')
        .fill('Admin Notification');
      await authenticatedPage
        .getByTestId('ns-notification-submit-btn')
        .click();

      // Verify created
      await expect(
        authenticatedPage.getByText('Admin Notification'),
      ).toBeVisible();

      // Delete the notification
      const kebabToggle = authenticatedPage
        .locator('[data-testid$="-ns-toggle-kebab"]')
        .first();
      await kebabToggle.click();
      const deleteButton = authenticatedPage
        .locator('[data-testid$="-delete-notification"]')
        .first();
      await deleteButton.click();
      await authenticatedPage
        .getByTestId('confirm-delete-ns-notification')
        .click();

      // Verify deleted
      await expect(
        authenticatedPage.getByText('No notifications configured'),
      ).toBeVisible();
    });

    test('non-admin org member cannot access notification management', async ({
      authenticatedPage,
      superuserApi,
    }) => {
      // Create org as superuser — testuser is NOT an admin
      const org = await superuserApi.organization('nsnotifnoadmin');

      // Add testuser as a member via a team with 'member' role
      const team = await superuserApi.team(org.name, 'members', 'member');
      await superuserApi.teamMember(
        org.name,
        team.name,
        TEST_USERS.user.username,
      );

      // Navigate to org settings as non-admin testuser
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Either the Notifications tab is hidden, or the create button is not available
      const notifTab = authenticatedPage.getByTestId('Notifications');
      if (await notifTab.isVisible()) {
        await notifTab.click();
        await expect(
          authenticatedPage.getByTestId('create-ns-notification-btn'),
        ).not.toBeVisible();
      }
    });

    test('superuser can manage notifications on any org via API', async ({
      superuserApi,
      api,
    }) => {
      // Create org as testuser
      const org = await api.organization('nsnotifsu');

      // Superuser creates a notification on testuser's org
      const notification = await superuserApi.namespaceNotification(
        org.name,
        'quota_warning',
        'webhook',
        {url: 'https://example.com/hook'},
        {},
        'Superuser Notification',
      );

      // Verify notification exists
      const list =
        await superuserApi.raw.getNamespaceNotifications(org.name);
      expect(list.notifications).toHaveLength(1);
      expect(list.notifications[0].uuid).toBe(notification.uuid);

      // Superuser deletes it
      await superuserApi.raw.deleteNamespaceNotification(
        org.name,
        notification.uuid,
      );

      // Verify deleted
      const listAfter =
        await superuserApi.raw.getNamespaceNotifications(org.name);
      expect(listAfter.notifications).toHaveLength(0);
    });

    test('unauthenticated API requests are rejected', async ({
      api,
      anonClient,
    }) => {
      const org = await api.organization('nsnotifanon');

      // Attempt to list notifications without authentication
      const response = await anonClient.get(
        `/api/v1/organization/${org.name}/notifications`,
      );

      expect([401, 403]).toContain(response.status());
    });
  },
);
