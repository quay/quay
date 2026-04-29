import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe('External Logins Tab', {tag: ['@user', '@auth:OIDC']}, () => {
  test('tab visible for own user account when not single-signin', async ({
    authenticatedPage,
    quayConfig,
  }) => {
    // Tab is hidden when there is exactly one external provider and
    // DIRECT_LOGIN is not enabled (single-signin mode)
    const externalLogins = quayConfig?.external_login ?? [];
    const isSingleSignin =
      externalLogins.length === 1 && !quayConfig?.features?.DIRECT_LOGIN;

    await authenticatedPage.goto(`/user/${TEST_USERS.user.username}`);

    const tab = authenticatedPage.getByRole('tab', {
      name: /External login/i,
    });

    if (isSingleSignin) {
      await expect(tab).not.toBeVisible();
    } else {
      await expect(tab).toBeVisible();
      await tab.click();
      await expect(
        authenticatedPage.getByTestId('external-logins-tab'),
      ).toBeVisible();
    }
  });

  test('shows providers or no-providers alert', async ({
    authenticatedPage,
    quayConfig,
  }) => {
    const externalLogins = quayConfig?.external_login ?? [];
    const isSingleSignin =
      externalLogins.length === 1 && !quayConfig?.features?.DIRECT_LOGIN;

    test.skip(isSingleSignin, 'Tab hidden in single-signin mode');

    await authenticatedPage.goto(
      `/user/${TEST_USERS.user.username}?tab=Externallogins`,
    );

    const noProvidersAlert = authenticatedPage.getByTestId(
      'no-external-providers-alert',
    );
    const providerTable = authenticatedPage.getByTestId('external-logins-tab');

    await expect(noProvidersAlert.or(providerTable)).toBeVisible();
  });

  test('tab not visible for organizations', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('extloginorg');

    await authenticatedPage.goto(`/organization/${org.name}`);

    await expect(
      authenticatedPage.getByRole('tab', {name: /External login/i}),
    ).not.toBeVisible();
  });
});
