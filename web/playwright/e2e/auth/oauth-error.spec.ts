import {test, expect} from '../../fixtures';

test.describe('OAuth Error Page', {tag: ['@auth']}, () => {
  test('displays error page with provider name and decoded error message', async ({
    unauthenticatedPage: page,
  }) => {
    await page.goto(
      '/oauth-error?error_description=GitHub:%20The%20email%20address%20test@example.com%20is%20already%20associated%20with%20an%20existing%20account&provider=GitHub',
    );

    await expect(page.getByText('GitHub Authentication Error')).toBeVisible();
    await expect(
      page.getByText(
        'The email address test@example.com is already associated with an existing account',
      ),
    ).toBeVisible();
    await expect(page.getByText('Return to Sign In')).toBeVisible();
  });

  test('displays registration hint when register_redirect and user_creation are true', async ({
    unauthenticatedPage: page,
  }) => {
    await page.goto(
      '/oauth-error?error_description=Account%20not%20found&provider=Google&register_redirect=true&user_creation=true',
    );

    await expect(page.getByText('Account not found')).toBeVisible();
    await expect(page.getByText('Account Registration Required')).toBeVisible();
    await expect(
      page.getByText(
        'You will be able to reassociate this Google account to your new account in the user settings panel',
      ),
    ).toBeVisible();
  });

  test('shows fallback message when error_description is missing and default provider when provider is missing', async ({
    unauthenticatedPage: page,
  }) => {
    // No error_description, no provider
    await page.goto('/oauth-error?provider=GitHub');
    await expect(page.getByText('GitHub Authentication Error')).toBeVisible();
    await expect(
      page.getByText('An unknown error occurred during authentication'),
    ).toBeVisible();

    // No provider param → default provider name
    await page.goto('/oauth-error?error_description=Some%20error%20occurred');
    await expect(
      page.getByText('OAuth Provider Authentication Error'),
    ).toBeVisible();
    await expect(page.getByText('Some error occurred')).toBeVisible();
  });

  test('Return to Sign In button navigates to signin page', async ({
    unauthenticatedPage: page,
  }) => {
    await page.goto(
      '/oauth-error?error_description=Test%20error&provider=GitHub',
    );

    await page.getByText('Return to Sign In').click();
    await expect(page).toHaveURL(/\/signin/);
  });

  test(
    'OAuth callback error ignores an attacker-controlled Referer',
    {tag: ['@PROJQUAY-10658', '@auth:OIDC']},
    async ({unauthenticatedPage: page, quayConfig}) => {
      test.skip(
        !quayConfig?.external_login?.length,
        'Requires an external login provider',
      );

      const provider = quayConfig.external_login[0];
      await page.goto('/signin');
      const authResponsePromise = page.waitForResponse(
        (response) =>
          response.url().includes(`/api/v1/externallogin/${provider.id}`) &&
          response.request().method() === 'POST',
      );
      await page.getByTestId(`external-login-${provider.id}`).click();
      const authResponse = await authResponsePromise;
      expect(authResponse.status()).toBe(200);

      const {auth_url: authUrl} = await authResponse.json();
      const authorizationUrl = new URL(authUrl);
      const redirectUri = authorizationUrl.searchParams.get('redirect_uri');
      const state = authorizationUrl.searchParams.get('state');
      expect(redirectUri).toBeTruthy();
      expect(state).toBeTruthy();

      const callbackUrl = new URL(redirectUri!);
      callbackUrl.searchParams.set('state', state!);
      callbackUrl.searchParams.set('error', 'access_denied');
      const response = await page.request.get(callbackUrl.toString(), {
        headers: {Referer: 'https://evil.attacker.com/phishing'},
        maxRedirects: 0,
      });

      expect(response.status()).toBe(302);
      const location = new URL(response.headers()['location']);
      expect(location.origin).toBe(callbackUrl.origin);
      expect(location.pathname).toBe('/oauth-error');
    },
  );
});
