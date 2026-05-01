import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

test.describe('LDAP Login', {tag: ['@auth', '@auth:LDAP', '@critical']}, () => {
  test('logs in with LDAP credentials', async ({browser, quayConfig}) => {
    test.skip(
      quayConfig?.config?.AUTHENTICATION_TYPE !== 'LDAP',
      'Requires AUTHENTICATION_TYPE: LDAP',
    );

    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto('/signin');

    await page
      .getByRole('textbox', {name: /username/i})
      .fill(TEST_USERS.user.username);
    await page.getByLabel(/password/i).fill(TEST_USERS.user.password);
    await page.locator('button[type="submit"]').click();

    await expect(page).toHaveURL(/\/(organization|updateuser|repository)/, {
      timeout: 15000,
    });

    await expect(page).not.toHaveURL(/\/signin/);

    await page.close();
    await context.close();
  });

  test('superuser can log in with LDAP credentials', async ({
    browser,
    quayConfig,
  }) => {
    test.skip(
      quayConfig?.config?.AUTHENTICATION_TYPE !== 'LDAP',
      'Requires AUTHENTICATION_TYPE: LDAP',
    );

    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto('/signin');

    await page
      .getByRole('textbox', {name: /username/i})
      .fill(TEST_USERS.admin.username);
    await page.getByLabel(/password/i).fill(TEST_USERS.admin.password);
    await page.locator('button[type="submit"]').click();

    await expect(page).toHaveURL(/\/(organization|updateuser|repository)/, {
      timeout: 15000,
    });

    await expect(page).not.toHaveURL(/\/signin/);

    await page.close();
    await context.close();
  });

  test('rejects invalid LDAP credentials', async ({browser, quayConfig}) => {
    test.skip(
      quayConfig?.config?.AUTHENTICATION_TYPE !== 'LDAP',
      'Requires AUTHENTICATION_TYPE: LDAP',
    );

    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto('/signin');

    await page
      .getByRole('textbox', {name: /username/i})
      .fill('nonexistentuser');
    await page.getByLabel(/password/i).fill('wrongpassword');
    await page.locator('button[type="submit"]').click();

    await expect(page.getByText('Invalid Username or Password')).toBeVisible();
    await expect(page).toHaveURL(/\/signin/);

    await page.close();
    await context.close();
  });

  test('does not show create account link for LDAP auth', async ({
    unauthenticatedPage: page,
    quayConfig,
  }) => {
    test.skip(
      quayConfig?.config?.AUTHENTICATION_TYPE !== 'LDAP',
      'Requires AUTHENTICATION_TYPE: LDAP',
    );

    await page.goto('/signin');

    await expect(page.getByRole('textbox', {name: /username/i})).toBeVisible();
    await expect(
      page.getByTestId('signin-create-account-link'),
    ).not.toBeVisible();
  });

  test('does not show forgot password link for LDAP auth', async ({
    unauthenticatedPage: page,
    quayConfig,
  }) => {
    test.skip(
      quayConfig?.config?.AUTHENTICATION_TYPE !== 'LDAP',
      'Requires AUTHENTICATION_TYPE: LDAP',
    );

    await page.goto('/signin');

    await expect(page.getByRole('textbox', {name: /username/i})).toBeVisible();
    await expect(
      page.getByTestId('signin-forgot-password-link'),
    ).not.toBeVisible();
  });
});
