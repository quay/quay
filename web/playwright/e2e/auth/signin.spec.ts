import {test as base, expect} from '../../fixtures';

const test = base;

test.describe(
  'Signin page with anonymous access disabled',
  {tag: ['@auth', '@critical', '@PROJQUAY-10090']},
  () => {
    test('does not cause infinite redirect loop when API returns 401', async ({
      browser,
    }) => {
      // Create a fresh context without any authentication
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

      // Navigate to signin page
      await page.goto('/signin');

      // Wait for the page to stabilize (give time for any potential redirects)
      await page.waitForTimeout(2000);

      // Verify we're still on the signin page
      await expect(page).toHaveURL(/\/signin/);

      // Verify the login form is visible (page rendered successfully)
      await expect(
        page.getByRole('textbox', {name: /username/i}),
      ).toBeVisible();

      // Verify no infinite redirect loop occurred
      // Should have only 1-2 requests to /signin (initial + possible soft navigation)
      expect(signinRequests.length).toBeLessThanOrEqual(2);

      // Cleanup
      await page.close();
      await context.close();
    });

    test('signin page renders login form correctly with 401 on messages API', async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await context.newPage();

      // Mock /api/v1/messages to return 401
      await page.route('**/api/v1/messages', (route) =>
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({message: 'Anonymous access is not allowed'}),
        }),
      );

      await page.goto('/signin');

      // Verify login form elements are present
      await expect(page.getByText('Log in to your account')).toBeVisible();
      await expect(
        page.getByRole('textbox', {name: /username/i}),
      ).toBeVisible();
      await expect(page.getByLabel(/password/i)).toBeVisible();

      // Cleanup
      await page.close();
      await context.close();
    });

    test('does not redirect when already on createaccount page with 401', async ({
      browser,
    }) => {
      const context = await browser.newContext();
      const page = await context.newPage();

      // Track redirects
      let redirectCount = 0;
      page.on('request', (request) => {
        if (
          request.url().includes('/signin') &&
          request.isNavigationRequest()
        ) {
          redirectCount++;
        }
      });

      // Mock /api/v1/messages to return 401
      await page.route('**/api/v1/messages', (route) =>
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({message: 'Anonymous access is not allowed'}),
        }),
      );

      // Navigate to create account page
      await page.goto('/createaccount');

      // Wait for any potential redirects
      await page.waitForTimeout(1000);

      // Should stay on createaccount page, not redirect to signin
      await expect(page).toHaveURL(/\/createaccount/);

      // Should not have redirected to signin
      expect(redirectCount).toBe(0);

      // Cleanup
      await page.close();
      await context.close();
    });
  },
);
