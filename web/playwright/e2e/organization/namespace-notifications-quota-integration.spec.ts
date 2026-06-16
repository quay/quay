import {test, expect} from '../../fixtures';

test.describe(
  'Namespace Notifications — Quota Integration',
  {
    tag: [
      '@organization',
      '@feature:QUOTA_NOTIFICATIONS',
      '@feature:QUOTA_MANAGEMENT',
      '@feature:EDIT_QUOTA',
    ],
  },
  () => {
    test('Quota tab and Notifications tab are independent', async ({
      authenticatedPage,
      api,
      superuserApi,
    }) => {
      const org = await api.organization('nsquotaindep');
      await superuserApi.quota(org.name, 10737418240); // 10 GiB

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Click Quota tab — shows quota configuration
      await authenticatedPage.getByTestId('Quota').click();
      await expect(
        authenticatedPage.getByTestId('quota-value-input'),
      ).toBeVisible();
      // Notification content should NOT be visible in Quota tab
      await expect(
        authenticatedPage.getByTestId('create-ns-notification-btn'),
      ).not.toBeVisible();

      // Click Notifications tab — shows notification config
      await authenticatedPage.getByTestId('Notifications').click();
      await expect(
        authenticatedPage.getByTestId('create-ns-notification-btn'),
      ).toBeVisible();
      // Quota content should NOT be visible in Notifications tab
      await expect(
        authenticatedPage.getByTestId('quota-value-input'),
      ).not.toBeVisible();
    });

    test('Notifications tab works without quota configured', async ({
      authenticatedPage,
      api,
    }) => {
      // Create org WITHOUT any quota
      const org = await api.organization('nsquotanone');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      // Create a webhook notification — should work without quota
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
        .fill('https://example.com/no-quota-hook');
      await authenticatedPage
        .getByTestId('ns-notification-title')
        .fill('No Quota Notification');
      await authenticatedPage
        .getByTestId('ns-notification-submit-btn')
        .click();

      // Notification created successfully without quota
      await expect(
        authenticatedPage.getByText('No Quota Notification'),
      ).toBeVisible();
      await expect(authenticatedPage.getByText('Enabled')).toBeVisible();
    });

    test('superuser-set quota does not affect admin notification management', async ({
      authenticatedPage,
      superuserApi,
      api,
    }) => {
      const org = await api.organization('nsquotasu');

      // Superuser sets quota with warning limit
      const quota = await superuserApi.quota(org.name, 104857600); // 100 MiB
      await superuserApi.raw.createQuotaLimit(
        org.name,
        quota.quotaId,
        'Warning',
        70,
      );

      // As testuser (org admin), navigate to Notifications tab
      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);
      await authenticatedPage.getByTestId('Notifications').click();

      // Testuser can create notification configs
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
        .fill('https://example.com/admin-hook');
      await authenticatedPage
        .getByTestId('ns-notification-title')
        .fill('Admin Created');
      await authenticatedPage
        .getByTestId('ns-notification-submit-btn')
        .click();

      await expect(
        authenticatedPage.getByText('Admin Created'),
      ).toBeVisible();

      // Verify quota tab shows read-only (set by superuser)
      await authenticatedPage.getByTestId('Quota').click();
      await expect(
        authenticatedPage.getByTestId('readonly-quota-alert'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('quota-value-input'),
      ).toBeDisabled();

      // Go back to Notifications — admin's notification still works
      await authenticatedPage.getByTestId('Notifications').click();
      await expect(
        authenticatedPage.getByText('Admin Created'),
      ).toBeVisible();
    });
  },
);
