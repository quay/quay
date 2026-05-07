import {test, expect} from '../../fixtures';

const hasGitHubLogin = (quayConfig: {external_login?: Array<{id: string}>}) =>
  quayConfig?.external_login?.some((p) => p.id === 'github');

test.describe('GitHub OAuth Login', {tag: ['@auth', '@auth:GitHub']}, () => {
  test('logs in via mock GitHub OAuth provider', async ({
    browser,
    quayConfig,
  }) => {
    test.skip(!hasGitHubLogin(quayConfig), 'GitHub login not configured');

    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto('/signin');

    await page.getByTestId('external-login-github').click();

    // Should be redirected to mock GitHub login page
    await page.waitForURL(/.*9090.*authorize/, {timeout: 15000});

    // Select user and approve
    await page.selectOption('select[name="username"]', 'testuser_github');
    await page.getByRole('button', {name: 'Login'}).click();

    // Should be redirected back to Quay and logged in
    await page.waitForURL(
      /.*localhost.*(organization|updateuser|repository).*/,
      {timeout: 15000},
    );

    await expect(page).not.toHaveURL(/\/signin/);
    await expect(page).not.toHaveURL(/\/oauth-error/);

    await page.close();
    await context.close();
  });

  test('first-time GitHub user creates Quay account', async ({
    browser,
    quayConfig,
  }) => {
    test.skip(!hasGitHubLogin(quayConfig), 'GitHub login not configured');

    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto('/signin');

    await page.getByTestId('external-login-github').click();

    // Login with a different user
    await page.waitForURL(/.*9090.*authorize/, {timeout: 15000});
    await page.selectOption('select[name="username"]', 'admin_github');
    await page.getByRole('button', {name: 'Login'}).click();

    // Should be redirected back to Quay (may go to updateuser for first-time setup)
    await page.waitForURL(
      /.*localhost.*(organization|updateuser|repository|oauth2).*/,
      {timeout: 15000},
    );

    await expect(page).not.toHaveURL(/\/signin/);
    await expect(page).not.toHaveURL(/\/oauth-error/);

    await page.close();
    await context.close();
  });
});
