import {test, expect} from '../../fixtures';

const hasGitHubLogin = (quayConfig: {external_login?: Array<{id: string}>}) =>
  quayConfig?.external_login?.some((p) => p.id === 'github');

test.describe('OAuth Callback Routing', {tag: ['@auth']}, () => {
  test('redirects to error page when user denies access', async ({
    unauthenticatedPage: page,
    quayConfig,
  }) => {
    test.skip(!hasGitHubLogin(quayConfig), 'GitHub login not configured');

    await page.goto('/signin');

    await page.getByTestId('external-login-github').click();

    // Wait for redirect to mock GitHub authorize page
    await page.waitForURL(/.*9090.*authorize/, {timeout: 15000});

    // Click "Deny" to trigger error callback
    await page.getByRole('button', {name: 'Deny'}).click();

    // Should be redirected back to Quay's /oauth-error page
    await expect(page).toHaveURL(/\/oauth-error/, {timeout: 15000});
    expect(page.url()).toContain('error');
  });

  test('redirects to error page with provider name', async ({
    unauthenticatedPage: page,
    quayConfig,
  }) => {
    test.skip(!hasGitHubLogin(quayConfig), 'GitHub login not configured');

    await page.goto('/signin');

    // Intercept the authorize redirect to inject force_error param
    await page.route(/\/login\/oauth\/authorize/, (route) => {
      const url = new URL(route.request().url());
      url.searchParams.set('force_error', 'server_error');
      route.continue({url: url.toString()});
    });

    await page.getByTestId('external-login-github').click();

    // Mock sees force_error and redirects with error param
    await expect(page).toHaveURL(/\/oauth-error/, {timeout: 15000});
    expect(page.url()).toContain('provider=');
  });
});
