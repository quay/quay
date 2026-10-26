import {test, expect} from '../../fixtures';
import {requestCsrfToken} from '../../utils/api/csrf';
import {BASE_URL} from '../../utils/config';

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
      const provider = quayConfig?.external_login?.[0];
      if (!provider) {
        test.skip(true, 'Requires an external login provider');
        return;
      }

      // Exercise the backend callback without depending on sign-in UI timing.
      const context = page.context();
      await context.addCookies([
        {
          name: 'patternfly',
          value: 'react',
          domain: new URL(BASE_URL).hostname,
          path: '/',
        },
      ]);
      const csrfToken = await requestCsrfToken(context.request, BASE_URL);
      const authResponse = await context.request.post(
        `${BASE_URL}/api/v1/externallogin/${provider.id}`,
        {
          data: {kind: 'login'},
          headers: {'X-CSRF-Token': csrfToken},
        },
      );
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
      const response = await context.request.get(callbackUrl.toString(), {
        headers: {Referer: 'https://evil.attacker.com/phishing'},
        maxRedirects: 0,
      });

      expect(response.status()).toBe(302);
      const locationHeader = response.headers()['location'];
      expect(locationHeader).toBeTruthy();
      const location = new URL(locationHeader);
      expect(location.origin).toBe(new URL(BASE_URL).origin);
      expect(location.pathname).toBe('/oauth-error');
      expect(location.searchParams.get('error')).toBe('oauth_error');
      expect(location.searchParams.get('error_description')).toBe(
        'access_denied',
      );
      expect(location.searchParams.get('provider')).toBe(provider.title);
      expect(location.href).not.toContain('evil.attacker.com');
    },
  );
});
