import {test, expect} from '../../fixtures';

test.describe('OAuth Callback Routing', {tag: ['@auth']}, () => {
  test('redirects to error page when callback has error param', async ({
    unauthenticatedPage: page,
  }) => {
    await page.goto(
      '/oauth2/github/callback?error=access_denied&error_description=User%20denied%20access',
    );

    await expect(page).toHaveURL(/\/oauth-error/, {timeout: 10000});
    expect(page.url()).toContain('error=access_denied');
    expect(page.url()).toContain('provider=github');
  });

  test('redirects to error page with error as description when description is missing', async ({
    unauthenticatedPage: page,
  }) => {
    await page.goto('/oauth2/github/callback?error=server_error');

    await expect(page).toHaveURL(/\/oauth-error/, {timeout: 10000});
    expect(page.url()).toContain('error_description=server_error');
  });

  test('handles attach flow error redirect', async ({
    unauthenticatedPage: page,
  }) => {
    await page.goto(
      '/oauth2/github/callback/attach?error=already_attached&error_description=Account%20already%20attached',
    );

    await expect(page).toHaveURL(/\/oauth-error/, {timeout: 10000});
    expect(page.url()).toContain('error=already_attached');
  });

  test('handles CLI token flow error redirect', async ({
    unauthenticatedPage: page,
  }) => {
    await page.goto(
      '/oauth2/github/callback/cli?error=invalid_request&error_description=Invalid%20CLI%20token%20request',
    );

    await expect(page).toHaveURL(/\/oauth-error/, {timeout: 10000});
    expect(page.url()).toContain('error=invalid_request');
  });
});
