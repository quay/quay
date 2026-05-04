import {test, expect} from '../../fixtures';

test.describe(
  'OIDC Login via Keycloak',
  {tag: ['@auth', '@auth:OIDC', '@critical']},
  () => {
    test('logs in via Keycloak OIDC provider', async ({
      browser,
      quayConfig,
    }) => {
      test.skip(
        !quayConfig?.external_login?.length,
        'No external login providers configured',
      );

      const context = await browser.newContext();
      const page = await context.newPage();

      await page.goto('/signin');

      // Find and click the OIDC login button
      const provider = quayConfig.external_login?.[0];
      if (!provider) return;
      await page.getByTestId(`external-login-${provider.id}`).click();

      // Should be redirected to Keycloak login page
      await page.waitForURL(/.*realms\/quay.*/, {timeout: 15000});

      // Fill in Keycloak credentials
      await page.fill('#username', 'testuser_oidc');
      await page.fill('#password', 'password');
      await page.click('#kc-login');

      // Should be redirected back to Quay and logged in
      await page.waitForURL(
        /.*localhost.*(organization|updateuser|repository).*/,
        {
          timeout: 15000,
        },
      );

      // Verify we're logged in and not on an error route
      await expect(page).not.toHaveURL(/\/signin/);
      await expect(page).not.toHaveURL(/\/oauth-error/);

      await page.close();
      await context.close();
    });

    test('first-time OIDC user creates Quay account', async ({
      browser,
      quayConfig,
    }) => {
      test.skip(
        !quayConfig?.external_login?.length,
        'No external login providers configured',
      );

      const context = await browser.newContext();
      const page = await context.newPage();

      await page.goto('/signin');

      const provider = quayConfig.external_login?.[0];
      if (!provider) return;
      await page.getByTestId(`external-login-${provider.id}`).click();

      // Login with a user that hasn't logged into Quay before
      await page.waitForURL(/.*realms\/quay.*/, {timeout: 15000});
      await page.fill('#username', 'readonly_oidc');
      await page.fill('#password', 'password');
      await page.click('#kc-login');

      // Should be redirected back to Quay (may go to updateuser for first-time setup)
      await page.waitForURL(
        /.*localhost.*(organization|updateuser|repository|oauth2).*/,
        {timeout: 15000},
      );

      // Verify not on error or signin routes
      await expect(page).not.toHaveURL(/\/signin/);
      await expect(page).not.toHaveURL(/\/oauth-error/);

      await page.close();
      await context.close();
    });
  },
);
