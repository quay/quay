import {test, expect} from '../../fixtures';
import {mailpit} from '../../utils/mailpit';

test.describe(
  'Namespace Notifications — User Namespace API',
  {tag: ['@feature:QUOTA_NOTIFICATIONS']},
  () => {
    test('user can create, list, and delete notifications for own namespace', async ({
      api,
    }) => {
      // Create notification for user's own namespace
      const notification = await api.userNamespaceNotification(
        'quota_warning',
        'webhook',
        {url: 'https://example.com/user-hook'},
        {},
        'User Webhook',
      );
      expect(notification.uuid).toBeTruthy();

      // List notifications
      const list = await api.raw.getUserNamespaceNotifications();
      expect(list.notifications.length).toBeGreaterThanOrEqual(1);
      const found = list.notifications.find(
        (n) => n.uuid === notification.uuid,
      );
      expect(found).toBeDefined();
      expect(found!.title).toBe('User Webhook');
      expect(found!.event).toBe('quota_warning');
      expect(found!.method).toBe('webhook');

      // Delete notification
      await api.raw.deleteUserNamespaceNotification(notification.uuid);

      // Verify deleted
      const listAfter = await api.raw.getUserNamespaceNotifications();
      const gone = listAfter.notifications.find(
        (n) => n.uuid === notification.uuid,
      );
      expect(gone).toBeUndefined();
    });

    test('user cannot manage notifications for another user namespace', async ({
      userClient,
      adminClient,
    }) => {
      // Create notification as admin for their own namespace
      const createResp = await adminClient.post(
        '/api/v1/user/notifications',
        {
          event: 'quota_warning',
          method: 'webhook',
          config: {url: 'https://example.com/admin-hook'},
          eventConfig: {},
          title: 'Admin Own Notification',
        },
      );
      expect(createResp.status()).toBe(201);
      const {uuid} = await createResp.json();

      // Regular user attempts to delete admin's notification
      const deleteResp = await userClient.delete(
        `/api/v1/user/notifications/${uuid}`,
      );
      // Should get 404 (notification belongs to different user)
      expect([403, 404]).toContain(deleteResp.status());

      // Clean up — admin deletes own notification
      await adminClient.delete(`/api/v1/user/notifications/${uuid}`);
    });

    test(
      'user email notification uses own email address',
      {tag: ['@feature:MAILING']},
      async ({api}) => {
        // Create email notification for user namespace
        const notification = await api.userNamespaceNotification(
          'quota_warning',
          'email',
          {email: 'testuser@example.com'},
          {},
          'User Email Test',
        );

        // Clear inbox and fire test notification
        await mailpit.clearInbox();
        await api.raw.testUserNamespaceNotification(notification.uuid);

        // Verify email delivered to user's address
        const email = await mailpit.waitForEmail(
          (msg) =>
            msg.To.some(
              (to) => to.Address === 'testuser@example.com',
            ),
          15_000,
        );
        expect(email).not.toBeNull();
      },
    );
  },
);
