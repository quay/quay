import {test, expect} from '../../fixtures';
import {pushImage} from '../../utils/container';
import {TEST_USERS} from '../../global-setup';

test.describe('Notification Drawer', {tag: ['@ui', '@container']}, () => {
  // Runs the two tests in this file in order on one worker: both push
  // notifications to the same user, and fullyParallel would let the badge
  // test's 6 pushes evict this test's notification from the drawer's 5-slot
  // backend limit before it asserts on it.
  test.describe.configure({mode: 'default'});

  test('notification drawer e2e: create, display, read, delete', async ({
    authenticatedPage,
    api,
  }) => {
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

  test(
    'notification bell badge shows N+ when more than 5 notifications exist',
    {tag: '@PROJQUAY-9038'},
    async ({authenticatedPage, api}) => {
      test.setTimeout(120_000);
      const namespace = TEST_USERS.user.username;

      // 1. Create repository
      const repo = await api.repository(namespace, 'notif-repo-badge');

      // 2. Configure quay_notification for repo_push targeting the user
      await api.raw.createRepositoryNotification(
        namespace,
        repo.name,
        'repo_push',
        'quay_notification',
        {target: {name: namespace, kind: 'user'}},
        {},
        'Test push notification for badge overflow',
      );

      // 3. Push 6 tags to trigger 6 push notifications (backend fetch limit is 5)
      for (let i = 0; i < 6; i++) {
        await pushImage(
          namespace,
          repo.name,
          `tag${i}`,
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        );
      }

      // Brief wait for notification processing
      await authenticatedPage.waitForTimeout(2000);

      // 4. Navigate and verify the bell shows "5+", not the plain count
      await authenticatedPage.goto('/organization');
      const bell = authenticatedPage.getByTestId('notification-bell');

      await expect(async () => {
        await authenticatedPage.reload();
        await expect(bell).toBeVisible();
        await expect(bell).toContainText('5+');
      }).toPass({timeout: 20000, intervals: [2000, 3000, 5000]});

      // Dismiss the notifications this test created so they don't linger on
      // the user for later runs/tests (repository deletion doesn't clean them up).
      const {notifications} = await api.raw.getUserNotifications(10);
      await Promise.all(
        notifications
          .filter((n) => n.metadata.repository === repo.fullName)
          .map((n) => api.raw.dismissUserNotification(n.id)),
      );
    },
  );
});
