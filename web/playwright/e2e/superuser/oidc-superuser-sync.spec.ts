import {test, expect} from '../../fixtures';

const SYNC_USER = {
  username: 'sync_oidc',
  password: 'password',
};

test.describe(
  'OIDC Superuser Group Sync',
  {tag: ['@auth:OIDC', '@feature:SUPERUSERS_FULL_ACCESS']},
  () => {
    test('user in OIDC superuser group gains superuser access after login', async ({
      browser,
      quayConfig,
    }) => {
      test.skip(
        !quayConfig?.external_login?.length,
        'No external login providers configured',
      );

      const context = await browser.newContext();
      try {
        const page = await context.newPage();

        // Login as sync_oidc via Keycloak (member of quay-superusers group)
        await page.goto('/signin');
        const provider = quayConfig.external_login![0];
        await page.getByTestId(`external-login-${provider.id}`).click();
        await page.waitForURL(/.*realms\/quay.*/, {timeout: 15000});
        await page.fill('#username', SYNC_USER.username);
        await page.fill('#password', SYNC_USER.password);
        await page.click('#kc-login');

        await page.waitForURL(
          (url) =>
            url.hostname === 'localhost' && !url.pathname.includes('/realms/'),
          {timeout: 15000},
        );

        // Navigate to organization page
        await page.goto('/organization');

        // Superuser nav section should be visible (synced from OIDC group)
        await expect(page.getByRole('button', {name: 'Superuser'})).toBeVisible(
          {timeout: 15000},
        );

        // Verify superuser pages are accessible
        await page.goto('/service-keys');
        await expect(
          page.getByRole('heading', {name: 'Service Keys', exact: true}),
        ).toBeVisible();

        await page.close();
      } finally {
        await context.close();
      }
    });

    test('user NOT in OIDC superuser group does not gain superuser access', async ({
      authenticatedPage,
    }) => {
      // authenticatedPage is testuser_oidc (not in quay-superusers group)
      await authenticatedPage.goto('/organization');

      await expect(
        authenticatedPage.getByRole('button', {name: 'Superuser'}),
      ).not.toBeVisible();

      // Direct navigation to superuser page redirects away
      await authenticatedPage.goto('/service-keys');
      await expect(authenticatedPage).toHaveURL(
        /.*\/(organization|repository).*/,
      );
    });
  },
);
