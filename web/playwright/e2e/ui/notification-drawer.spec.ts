import {test, expect, uniqueName} from '../../fixtures';
import {ApiClient} from '../../utils/api';
import {pushImage, isContainerRuntimeAvailable} from '../../utils/container';
import {TEST_USERS} from '../../global-setup';

test.describe('Notification Drawer', {tag: ['@ui', '@container']}, () => {
  test('notification drawer e2e: create, display, read, delete', async ({
    authenticatedPage,
    authenticatedRequest,
  }) => {
    // Check container runtime availability
    const runtimeAvailable = await isContainerRuntimeAvailable();
    test.skip(!runtimeAvailable, 'Container runtime (podman/docker) required');

    const namespace = TEST_USERS.user.username;
    const repoName = uniqueName('notif-repo');
    const api = new ApiClient(authenticatedRequest);

    try {
      // 1. Create repository
      await api.createRepository(namespace, repoName, 'private');

      // 2. Configure quay_notification for repo_push targeting the user
      await api.createRepositoryNotification(
        namespace,
        repoName,
        'repo_push',
        'quay_notification',
        {target: {name: namespace, kind: 'user'}},
        {},
        'Test push notification',
      );

      // 3. Push image to trigger notification
      await pushImage(
        namespace,
        repoName,
        'latest',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Poll API until notification appears
      await expect
        .poll(
          async () => {
            const {notifications} = await api.getUserNotifications();
            return notifications.some((n) => n.metadata?.name === repoName);
          },
          {
            message: `Waiting for notification for repo ${repoName}`,
            timeout: 10000,
          },
        )
        .toBe(true);

      // 4. Navigate and verify bell exists
      await authenticatedPage.goto('/organization');
      const bell = authenticatedPage.getByTestId('notification-bell');
      await expect(bell).toBeVisible();

      // 5. Click bell to open drawer
      await bell.click();
      const drawer = authenticatedPage.getByTestId('notification-drawer');
      await expect(drawer).toBeVisible();

      // 6. Verify our notification exists (find by repo name to avoid interference from other tests)
      const items = authenticatedPage.getByTestId('notification-item');
      const ourNotification = items.filter({hasText: repoName});
      await expect(ourNotification).toBeVisible();

      // 7. Mark our notification as read by clicking header
      await ourNotification.getByTestId('notification-header').click();
      await expect(ourNotification).toHaveClass(/pf-m-read/);

      // 8. Delete our notification
      await ourNotification.getByTestId('delete-notification').click();

      // 9. Verify our notification was removed
      await expect(ourNotification).not.toBeVisible();
    } finally {
      // Cleanup: delete repository
      try {
        await api.deleteRepository(namespace, repoName);
      } catch {
        // Already deleted or never created
      }
    }
  });
});
