import {test, expect} from '../../fixtures';

test.describe(
  'Namespace Notifications — Feature Flag',
  {tag: ['@organization', '@feature:QUOTA_NOTIFICATIONS']},
  () => {
    test('notifications tab is visible when feature flag is enabled', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotifflag');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Notifications tab should be visible (this test only runs when QUOTA_NOTIFICATIONS is enabled)
      await expect(
        authenticatedPage.getByTestId('Notifications'),
      ).toBeVisible();

      // Click the tab and verify content renders
      await authenticatedPage.getByTestId('Notifications').click();
      await expect(
        authenticatedPage.getByText('No notifications configured'),
      ).toBeVisible();
    });

    test('notifications tab is a standalone tab, not embedded in Quota', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('nsnotifstandalone');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Both tabs should exist as distinct, separate tabs
      const notificationsTab =
        authenticatedPage.getByTestId('Notifications');
      await expect(notificationsTab).toBeVisible();

      // Click Notifications tab — content should be notification-specific
      await notificationsTab.click();
      await expect(
        authenticatedPage.getByTestId('create-ns-notification-btn'),
      ).toBeVisible();

      // Quota-specific content should NOT be in the Notifications tab
      await expect(
        authenticatedPage.getByTestId('quota-value-input'),
      ).not.toBeVisible();
    });
  },
);
