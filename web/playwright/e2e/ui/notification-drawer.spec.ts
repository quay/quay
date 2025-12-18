import {test, expect} from '../../fixtures';
import {pushImage, isContainerRuntimeAvailable} from '../../utils/container';
import {TEST_USERS} from '../../global-setup';

test.describe('Notification Drawer', {tag: ['@ui', '@container']}, () => {
  test('notification drawer e2e: create, display, read, delete', async ({
    authenticatedPage,
    api,
  }) => {
    // Check container runtime availability
    const runtimeAvailable = await isContainerRuntimeAvailable();
    test.skip(!runtimeAvailable, 'Container runtime (podman/docker) required');

    const namespace = TEST_USERS.user.username;

    // 1. Create repository
    const repo = await api.repository(namespace, 'notif-repo');

    // 2. Configure quay_notification for repo_push targeting the user
    await api.raw.createRepositoryNotification(
      namespace,
      repo.name,
      'repo_push',
      'quay_notification',
      {target: {name: namespace, kind: 'user'}},
      {},
      'Test push notification',
    );

    // 3. Push image to trigger notification
    await pushImage(
      namespace,
      repo.name,
      'latest',
      TEST_USERS.user.username,
      TEST_USERS.user.password,
    );

    // Brief wait for notification processing
    await authenticatedPage.waitForTimeout(2000);

    // 4. Navigate and verify bell exists
    await authenticatedPage.goto('/organization');
    const bell = authenticatedPage.getByTestId('notification-bell');
    await expect(bell).toBeVisible();

    // 5. Click bell and wait for notification to appear (may need retries for backend processing)
    const drawer = authenticatedPage.getByTestId('notification-drawer');
    const ourNotification = authenticatedPage
      .getByTestId('notification-item')
      .filter({hasText: repo.name});

    await expect(async () => {
      await authenticatedPage.reload();
      await expect(bell).toBeVisible();
      await bell.click();
      await expect(drawer).toBeVisible();
      await expect(ourNotification).toBeVisible();
    }).toPass({timeout: 20000, intervals: [2000, 3000, 5000]});

    // 7. Mark our notification as read by clicking header
    await ourNotification.getByTestId('notification-header').click();
    await expect(ourNotification).toHaveClass(/pf-m-read/);

    // 8. Delete our notification
    await ourNotification.getByTestId('delete-notification').click();

    // 9. Verify our notification was removed
    await expect(ourNotification).not.toBeVisible();
  });
});
