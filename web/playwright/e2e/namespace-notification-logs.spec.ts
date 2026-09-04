import {test, expect, uniqueName} from '../fixtures';

test.describe(
  'Namespace Notification Log Descriptions',
  {tag: ['@logs', '@feature:QUOTA_NOTIFICATIONS', '@PROJQUAY-12232']},
  () => {
    test('create and delete namespace notification logs render descriptions', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization(uniqueName('nslogdesc'));

      // Create a namespace notification — generates create_namespace_notification log
      const notification = await api.namespaceNotification(
        org.name,
        'quota_warning',
        'webhook',
        {url: 'https://example.com/log-test'},
        {},
        'Log Test Webhook',
      );

      // Delete it via raw API — generates delete_namespace_notification log
      await api.raw.deleteNamespaceNotification(org.name, notification.uuid);

      // Navigate to the org's usage logs
      await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);

      const table = authenticatedPage.getByTestId('usage-logs-table');
      await expect(table).toBeVisible();

      // Verify create and delete logs each reference quota_warning in context
      await expect(
        table.getByText(/Add notification of event.*quota_warning/),
      ).toBeVisible();
      await expect(
        table.getByText(/Delete notification of event.*quota_warning/),
      ).toBeVisible();

      // Verify no "No description available" fallback
      await expect(
        table.getByText('No description available'),
      ).not.toBeAttached();
    });
  },
);
