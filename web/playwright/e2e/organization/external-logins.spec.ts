import {test, expect} from '../../fixtures';

test.describe(
  'External Logins Tab',
  {tag: ['@user', '@auth:OIDC', '@feature:DIRECT_LOGIN']},
  () => {
    test('tab renders with external logins heading', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto('/user/testuser?tab=Externallogins');

      const externalLoginsTab = authenticatedPage.getByTestId(
        'external-logins-tab',
      );
      await expect(externalLoginsTab).toBeVisible();
      await expect(
        authenticatedPage.getByText('External Logins'),
      ).toBeVisible();
    });

    test('shows no providers alert when none configured', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto('/user/testuser?tab=Externallogins');

      // If no external providers are configured, should show info alert
      const noProvidersAlert = authenticatedPage.getByTestId(
        'no-external-providers-alert',
      );
      const providerTable = authenticatedPage.getByRole('table');

      // Either the alert or the provider table should be visible
      await expect(noProvidersAlert.or(providerTable)).toBeVisible();
    });

    test('tab not visible for organizations', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('extloginorg');

      await authenticatedPage.goto(`/organization/${org.name}`);

      // External logins tab should not be present for organizations
      await expect(
        authenticatedPage.getByRole('tab', {name: /External login/i}),
      ).not.toBeVisible();
    });
  },
);
