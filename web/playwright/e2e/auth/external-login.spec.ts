import {test, expect} from '../../fixtures';

test.describe(
  'External Login Providers',
  {tag: ['@auth', '@auth:OIDC']},
  () => {
    test('displays external login buttons when OIDC is configured', async ({
      unauthenticatedPage: page,
      quayConfig,
    }) => {
      test.skip(
        !quayConfig?.external_login?.length,
        'No external login providers configured',
      );

      await page.goto('/signin');

      // Should display external login button(s)
      const loginButtons = page.locator('[data-testid^="external-login-"]');
      await expect(loginButtons.first()).toBeVisible();
    });

    test('external login button click triggers auth redirect', async ({
      unauthenticatedPage: page,
      quayConfig,
    }) => {
      test.skip(
        !quayConfig?.external_login?.length,
        'No external login providers configured',
      );

      const provider = quayConfig.external_login[0];
      await page.goto('/signin');

      // Intercept the external login API call to verify it fires
      const responsePromise = page.waitForResponse(
        (resp) =>
          resp.url().includes(`/api/v1/externallogin/${provider.id}`) &&
          resp.request().method() === 'POST',
      );

      await page.getByTestId(`external-login-${provider.id}`).click();

      const response = await responsePromise;
      expect(response.status()).toBe(200);
    });

    test('preserves redirect URL in external login flow', async ({
      unauthenticatedPage: page,
      quayConfig,
    }) => {
      test.skip(
        !quayConfig?.external_login?.length,
        'No external login providers configured',
      );

      await page.goto('/signin?redirect_url=/repository/test/repo');

      const provider = quayConfig.external_login[0];

      // Click external login and verify localStorage stores redirect
      const responsePromise = page.waitForResponse(
        (resp) =>
          resp.url().includes(`/api/v1/externallogin/${provider.id}`) &&
          resp.request().method() === 'POST',
      );

      await page.getByTestId(`external-login-${provider.id}`).click();

      await responsePromise;

      const state = await page.context().storageState();
      const quayOrigin = state.origins.find((o) =>
        o.origin.includes('localhost'),
      );
      const redirectEntry = quayOrigin?.localStorage.find(
        (e) => e.name === 'quay.redirectAfterLoad',
      );
      expect(redirectEntry?.value).toContain('/repository/test/repo');
    });
  },
);
