import {test as base, expect, uniqueName} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';

const test = base;

test.describe(
  'Signin page with anonymous access disabled',
  {tag: ['@auth', '@critical', '@PROJQUAY-10090']},
  () => {
    // These tests need route mocking, so they use browser.newContext()
    test('does not cause infinite redirect loop when API returns 401', async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await context.newPage();

      // Track network requests to detect redirect loops
      const signinRequests: string[] = [];
      page.on('request', (request) => {
        if (request.url().includes('/signin')) {
          signinRequests.push(request.url());
        }
      });

      // Mock /api/v1/messages to return 401 (simulating ANONYMOUS_ACCESS: false)
      await page.route('**/api/v1/messages', (route) =>
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({message: 'Anonymous access is not allowed'}),
        }),
      );

      await page.goto('/signin');
      await page.waitForTimeout(2000);

      await expect(page).toHaveURL(/\/signin/);
      await expect(
        page.getByRole('textbox', {name: /username/i}),
      ).toBeVisible();
      expect(signinRequests.length).toBeLessThanOrEqual(2);

      await page.close();
      await context.close();
    });

    test('signin page renders login form correctly with 401 on messages API', async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await context.newPage();

      await page.route('**/api/v1/messages', (route) =>
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({message: 'Anonymous access is not allowed'}),
        }),
      );

      await page.goto('/signin');

      await expect(page.getByText('Log in to your account')).toBeVisible();
      await expect(
        page.getByRole('textbox', {name: /username/i}),
      ).toBeVisible();
      await expect(page.getByLabel(/password/i)).toBeVisible();

      await page.close();
      await context.close();
    });

    test('does not redirect when already on createaccount page with 401', async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await context.newPage();

      let redirectCount = 0;
      page.on('request', (request) => {
        if (
          request.url().includes('/signin') &&
          request.isNavigationRequest()
        ) {
          redirectCount++;
        }
      });

      await page.route('**/api/v1/messages', (route) =>
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({message: 'Anonymous access is not allowed'}),
        }),
      );

      await page.goto('/createaccount');
      await page.waitForTimeout(1000);

      await expect(page).toHaveURL(/\/createaccount/);
      expect(redirectCount).toBe(0);

      await page.close();
      await context.close();
    });
  },
);

// Signin error handling tests
test.describe('Signin error handling', {tag: ['@auth', '@signin']}, () => {
  test('handles invalid credentials', async ({unauthenticatedPage}) => {
    await unauthenticatedPage.goto('/signin');

    // Use real API with wrong credentials
    await unauthenticatedPage
      .getByRole('textbox', {name: /username/i})
      .fill('nonexistentuser');
    await unauthenticatedPage.getByLabel(/password/i).fill('wrongpassword');
    await unauthenticatedPage.locator('button[type="submit"]').click();

    // Real API returns 403 with invalidCredentials: true
    await expect(
      unauthenticatedPage.getByText('Invalid Username or Password'),
    ).toBeVisible();
    await expect(unauthenticatedPage).toHaveURL(/\/signin/);
  });

  test(
    'handles unverified email',
    {tag: '@feature:MAILING'},
    async ({browser, superuserApi}) => {
      // Create user but don't verify email
      const username = uniqueName('unverified');
      const password = 'testpassword123';
      await superuserApi.raw.createUser(
        username,
        password,
        `${username}@example.com`,
      );

      // Use fresh browser context to ensure clean CSRF state
      const context = await browser.newContext();
      const page = await context.newPage();

      try {
        await page.goto('/signin');

        await page.getByRole('textbox', {name: /username/i}).fill(username);
        await page.getByLabel(/password/i).fill(password);
        await page.locator('button[type="submit"]').click();

        await expect(page.getByText(/verify your email/i)).toBeVisible();
        await expect(page).toHaveURL(/\/signin/);
      } finally {
        await page.close();
        await context.close();
        // Cleanup
        await superuserApi.raw.deleteUser(username);
      }
    },
  );

  // Tests that need route mocking use browser.newContext()
  test('handles CSRF token expiry', async ({browser}) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.route('**/api/v1/signin', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({error: 'CSRF token was invalid or missing'}),
      });
    });

    await page.goto('/signin');
    await page.getByRole('textbox', {name: /username/i}).fill('anyuser');
    await page.getByLabel(/password/i).fill('anypass');
    await page.locator('button[type="submit"]').click();

    await expect(page.getByText(/CSRF token expired/i)).toBeVisible();
    await expect(page).toHaveURL(/\/signin/);

    await page.close();
    await context.close();
  });

  test('shows user-friendly message for 500 server errors', async ({
    browser,
  }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    // Mock signin API endpoint to return 500 error
    await page.route('**/api/v1/signin', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({error: 'Internal server error'}),
      });
    });

    await page.goto('/signin');
    await page.getByRole('textbox', {name: /username/i}).fill('user1');
    await page.getByLabel(/password/i).fill('password');
    await page.locator('button[type="submit"]').click();

    // Wait for the error alert to appear
    const errorAlert = page.getByTestId('signin-error-alert');
    await expect(errorAlert).toBeVisible({timeout: 10000});
    // Should show user-friendly message, not raw HTTP status
    await expect(errorAlert).toContainText(/unable to sign in/i);
    await expect(page).toHaveURL(/\/signin/);

    await page.close();
    await context.close();
  });
});

// Signin navigation tests
test.describe(
  'Signin navigation',
  {tag: ['@auth', '@signin', '@auth:Database']},
  () => {
    test(
      'navigates to create account page via link',
      {tag: '@feature:USER_CREATION'},
      async ({unauthenticatedPage, quayConfig}) => {
        test.skip(
          quayConfig?.features?.INVITE_ONLY_USER_CREATION === true,
          'INVITE_ONLY_USER_CREATION must be disabled',
        );

        await unauthenticatedPage.goto('/signin');
        await unauthenticatedPage
          .getByTestId('signin-create-account-link')
          .click();

        await expect(unauthenticatedPage).toHaveURL(/\/createaccount/);
      },
    );

    test('redirects to organization after successful login', async ({
      browser,
    }) => {
      // Test the actual login flow (not pre-authenticated)
      const context = await browser.newContext();
      const page = await context.newPage();

      await page.goto('/signin');
      await page
        .getByRole('textbox', {name: /username/i})
        .fill(TEST_USERS.admin.username);
      await page.getByLabel(/password/i).fill(TEST_USERS.admin.password);
      await page.locator('button[type="submit"]').click();

      // After successful login, should redirect away from signin page
      // May go to /organization or /updateuser (if user has prompts)
      await expect(page).toHaveURL(/\/(organization|updateuser)/, {
        timeout: 10000,
      });

      await page.close();
      await context.close();
    });
  },
);

// Forgot Password functionality tests
test.describe(
  'Forgot Password functionality',
  {tag: ['@auth', '@signin', '@feature:MAILING', '@auth:Database']},
  () => {
    test('shows forgot password link and switches to recovery view', async ({
      unauthenticatedPage,
    }) => {
      await unauthenticatedPage.goto('/signin');

      await expect(
        unauthenticatedPage.getByTestId('signin-forgot-password-link'),
      ).toBeVisible();

      await unauthenticatedPage
        .getByTestId('signin-forgot-password-link')
        .click();

      await expect(
        unauthenticatedPage.getByText(/enter the e-mail address/i),
      ).toBeVisible();
      await expect(
        unauthenticatedPage.getByTestId('signin-back-to-login'),
      ).toBeVisible();

      await unauthenticatedPage.getByTestId('signin-back-to-login').click();

      await expect(
        unauthenticatedPage.getByRole('textbox', {name: /username/i}),
      ).toBeVisible();
    });

    test('sends recovery email successfully', async ({unauthenticatedPage}) => {
      // Use testuser's email which exists in the system
      await unauthenticatedPage.goto('/signin');
      await unauthenticatedPage
        .getByTestId('signin-forgot-password-link')
        .click();
      await unauthenticatedPage
        .getByTestId('signin-recovery-email')
        .fill('testuser@example.com');
      await unauthenticatedPage.getByTestId('signin-send-recovery').click();

      await expect(
        unauthenticatedPage.getByText(
          /Instructions on how to reset your password/i,
        ),
      ).toBeVisible();
    });

    test('handles organization account recovery', async ({
      unauthenticatedPage,
      api,
    }) => {
      // Create an org to test recovery with org email
      const org = await api.organization('recovery');

      await unauthenticatedPage.goto('/signin');
      await unauthenticatedPage
        .getByTestId('signin-forgot-password-link')
        .click();
      await unauthenticatedPage
        .getByTestId('signin-recovery-email')
        .fill(org.email);
      await unauthenticatedPage.getByTestId('signin-send-recovery').click();

      // Real API returns org response with admin info
      await expect(
        unauthenticatedPage.getByText(/assigned to organization/i),
      ).toBeVisible();
      // Org name appears in email (twice), verify at least one is visible
      await expect(
        unauthenticatedPage.getByText(org.name).first(),
      ).toBeVisible();
    });
  },
);

// Create Account visibility tests
test.describe(
  'Create Account visibility',
  {tag: ['@auth', '@signin', '@auth:Database', '@feature:USER_CREATION']},
  () => {
    test('shows create account link when conditions met', async ({
      unauthenticatedPage,
      quayConfig,
    }) => {
      test.skip(
        quayConfig?.features?.INVITE_ONLY_USER_CREATION === true,
        'INVITE_ONLY_USER_CREATION must be disabled',
      );

      await unauthenticatedPage.goto('/signin');

      await expect(
        unauthenticatedPage.getByTestId('signin-create-account-link'),
      ).toBeVisible();
      await expect(
        unauthenticatedPage.getByText(/Don't have an account/i),
      ).toBeVisible();
    });

    test(
      'shows invitation message when invite-only enabled',
      {tag: '@feature:INVITE_ONLY_USER_CREATION'},
      async ({unauthenticatedPage}) => {
        await unauthenticatedPage.goto('/signin');

        await expect(
          unauthenticatedPage.getByTestId('signin-invitation-message'),
        ).toBeVisible();
        await expect(
          unauthenticatedPage.getByTestId('signin-create-account-link'),
        ).not.toBeVisible();
      },
    );
  },
);

// Global Messages on Login Page tests
test.describe(
  'Global Messages on Login Page',
  {tag: ['@auth', '@signin', '@feature:SUPERUSERS_FULL_ACCESS']},
  () => {
    test('displays messages with different severities', async ({
      unauthenticatedPage,
      superuserApi,
    }) => {
      // Create real messages via API (auto-cleanup by superuserApi fixture)
      await superuserApi.message('Info message content', 'info');
      await superuserApi.message(
        '**Warning message**',
        'warning',
        'text/markdown',
      );
      await superuserApi.message('Error message content', 'error');

      await unauthenticatedPage.goto('/signin');

      await expect(
        unauthenticatedPage.getByText('Info message content'),
      ).toBeVisible();
      await expect(
        unauthenticatedPage.getByText('Warning message'),
      ).toBeVisible();
      await expect(
        unauthenticatedPage.getByText('Error message content'),
      ).toBeVisible();

      // Verify markdown is rendered (bold)
      await expect(
        unauthenticatedPage.locator('strong', {hasText: 'Warning message'}),
      ).toBeVisible();
    });

    test('renders markdown content with links', async ({
      unauthenticatedPage,
      superuserApi,
    }) => {
      await superuserApi.message(
        'Check our [terms](https://example.com/terms)',
        'info',
        'text/markdown',
      );

      await unauthenticatedPage.goto('/signin');

      const link = unauthenticatedPage.locator(
        'a[href="https://example.com/terms"]',
      );
      await expect(link).toBeVisible();
      await expect(link).toHaveAttribute('target', '_blank');
    });

    test('displays multiple messages simultaneously', async ({
      unauthenticatedPage,
      superuserApi,
    }) => {
      await superuserApi.message(
        'System Maintenance: Scheduled for Sunday 2AM-4AM EST',
        'warning',
      );
      await superuserApi.message(
        'Welcome to Red Hat Quay! Please review our updated terms.',
        'info',
      );
      await superuserApi.message(
        'Critical security update available.',
        'error',
      );

      await unauthenticatedPage.goto('/signin');

      await expect(
        unauthenticatedPage.getByText(/System Maintenance/),
      ).toBeVisible();
      await expect(
        unauthenticatedPage.getByText(/Welcome to Red Hat Quay/),
      ).toBeVisible();
      await expect(
        unauthenticatedPage.getByText(/Critical security update/),
      ).toBeVisible();
    });

    test('does not display messages section when empty', async ({
      unauthenticatedPage,
    }) => {
      await unauthenticatedPage.goto('/signin');

      // Login form should be visible
      await expect(
        unauthenticatedPage.getByRole('textbox', {name: /username/i}),
      ).toBeVisible();
      await expect(unauthenticatedPage.getByLabel(/password/i)).toBeVisible();

      // No global message banners should be present (no warning/error icons)
      // GlobalMessages renders nothing when empty, so check for absence of message indicators
      await expect(
        unauthenticatedPage.locator('svg[class*="exclamation-triangle"]'),
      ).not.toBeVisible();
      await expect(
        unauthenticatedPage.locator('svg[class*="times-circle"]'),
      ).not.toBeVisible();
    });
  },
);
