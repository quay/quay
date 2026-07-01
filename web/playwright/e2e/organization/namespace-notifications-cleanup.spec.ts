import {test, expect} from '../../fixtures';

test.describe(
  'Namespace Notifications — Cleanup on Deletion',
  {
    tag: [
      '@organization',
      '@feature:QUOTA_NOTIFICATIONS',
      '@feature:QUOTA_MANAGEMENT',
      '@feature:EDIT_QUOTA',
    ],
  },
  () => {
    test('deleting quota removes all namespace notification configs', async ({
      authenticatedPage,
      api,
      superuserApi,
    }) => {
      const org = await api.organization('nscleanquota');

      // Set quota
      const quota = await superuserApi.quota(org.name);

      // Create 2 namespace notifications
      await api.namespaceNotification(
        org.name,
        'quota_warning',
        'webhook',
        {url: 'https://example.com/hook1'},
        {},
        'Webhook Notification',
      );
      await api.namespaceNotification(
        org.name,
        'quota_error',
        'email',
        {email: 'admin@example.com'},
        {},
        'Email Notification',
      );

      // Verify notifications exist in UI
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();
      await expect(
        authenticatedPage.getByText('Webhook Notification'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Email Notification'),
      ).toBeVisible();

      // Delete the quota via API
      await superuserApi.raw.deleteOrganizationQuota(
        org.name,
        quota.quotaId,
      );

      // Reload notifications tab
      await authenticatedPage.reload();
      await authenticatedPage.getByTestId('Notifications').click();

      // Notifications should be cleaned up with the quota
      await expect(
        authenticatedPage.getByText('No notifications configured'),
      ).toBeVisible();
    });

    test('deleting a quota limit does NOT remove notification configs', async ({
      authenticatedPage,
      api,
      superuserApi,
    }) => {
      const org = await api.organization('nscleanlimit');

      // Set quota with warning limit
      const quota = await superuserApi.quota(org.name, 10737418240);
      await superuserApi.raw.createQuotaLimit(
        org.name,
        quota.quotaId,
        'Warning',
        80,
      );

      // Create a notification
      await api.namespaceNotification(
        org.name,
        'quota_warning',
        'webhook',
        {url: 'https://example.com/hook'},
        {},
        'Persistent Notification',
      );

      // Get limit ID to delete
      const quotas = await superuserApi.raw.getOrganizationQuota(org.name);
      const limitId = quotas[0].limits[0].id;

      // Delete the warning limit
      await superuserApi.raw.deleteQuotaLimit(
        org.name,
        quota.quotaId,
        limitId,
      );

      // Navigate to notifications tab — config should still exist
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      await expect(
        authenticatedPage.getByText('Persistent Notification'),
      ).toBeVisible();
    });

    test('re-creating quota after deletion starts fresh — notifications can be reconfigured', async ({
      authenticatedPage,
      api,
      superuserApi,
    }) => {
      const org = await api.organization('nscleanreset');

      // Set quota, create notification
      const quota = await superuserApi.quota(org.name);
      await api.namespaceNotification(
        org.name,
        'quota_warning',
        'webhook',
        {url: 'https://example.com/hook'},
        {},
        'Original Notification',
      );

      // Delete quota (cleans up notifications)
      await superuserApi.raw.deleteOrganizationQuota(
        org.name,
        quota.quotaId,
      );

      // Re-create quota
      await superuserApi.quota(org.name);

      // Navigate to notifications tab — should be empty (fresh start)
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      await expect(
        authenticatedPage.getByText('No notifications configured'),
      ).toBeVisible();

      // Create a new notification — should work
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
        .fill('https://example.com/hook-new');
      await authenticatedPage
        .getByTestId('ns-notification-title')
        .fill('Fresh Notification');
      await authenticatedPage
        .getByTestId('ns-notification-submit-btn')
        .click();

      await expect(
        authenticatedPage.getByText('Fresh Notification'),
      ).toBeVisible();
    });
  },
);
