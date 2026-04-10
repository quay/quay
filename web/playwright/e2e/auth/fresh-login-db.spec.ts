import {test, expect} from '../../fixtures';

test.describe(
  'Fresh Login - Database auth behavior',
  {tag: ['@auth', '@auth:Database']},
  () => {
    test('shows password modal (not redirect) on fresh_login_required', async ({
      superuserPage: page,
    }) => {
      // Mock the superuser endpoint to return fresh_login_required
      await page.route('**/api/v1/superuser/logs*', (route) =>
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({
            title: 'fresh_login_required',
            error_type: 'fresh_login_required',
            detail: 'The action requires a fresh login to succeed.',
          }),
        }),
      );

      await page.goto('/usage-logs');

      // For Database auth, should show password modal (not redirect to /signin)
      await expect(page.getByText('Please Verify', {exact: true})).toBeVisible({
        timeout: 10000,
      });
      await expect(page.getByPlaceholder('Current Password')).toBeVisible();

      // Should NOT have redirected to /signin (that's OIDC behavior)
      await expect(page).not.toHaveURL(/\/signin/);
    });

    test('wrong password closes modal and shows error alert', async ({
      superuserPage: page,
    }) => {
      // Mock the superuser endpoint to return fresh_login_required
      await page.route('**/api/v1/superuser/logs*', (route) =>
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({
            title: 'fresh_login_required',
            error_type: 'fresh_login_required',
            detail: 'The action requires a fresh login to succeed.',
          }),
        }),
      );

      // Mock verify endpoint to reject wrong password
      await page.route('**/api/v1/signin/verify', (route) =>
        route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({
            message: 'Invalid password',
            invalidCredentials: true,
          }),
        }),
      );

      await page.goto('/usage-logs');

      // Wait for the fresh login modal
      await expect(page.getByText('Please Verify', {exact: true})).toBeVisible({
        timeout: 10000,
      });

      // Enter wrong password and click Verify
      await page.getByPlaceholder('Current Password').fill('wrongpassword');
      await page.getByRole('button', {name: 'Verify'}).click();

      // Modal should close
      await expect(
        page.getByText('Please Verify', {exact: true}),
      ).not.toBeVisible({
        timeout: 5000,
      });

      // Error alert should be visible
      await expect(
        page.getByText('Invalid verification credentials'),
      ).toBeVisible({timeout: 5000});
    });

    test('correct password retries the queued operation', async ({
      superuserPage: page,
    }) => {
      let logsCallCount = 0;

      // First call returns fresh_login_required, subsequent calls pass through
      await page.route('**/api/v1/superuser/logs*', (route) => {
        logsCallCount++;
        if (logsCallCount === 1) {
          return route.fulfill({
            status: 401,
            contentType: 'application/json',
            body: JSON.stringify({
              title: 'fresh_login_required',
              error_type: 'fresh_login_required',
              detail: 'The action requires a fresh login to succeed.',
            }),
          });
        }
        // Second call (retry after verification): pass through to real server
        return route.continue();
      });

      // Mock verify endpoint to accept password
      await page.route('**/api/v1/signin/verify', (route) =>
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({success: true}),
          headers: {
            'x-next-csrf-token': 'new-csrf-token',
          },
        }),
      );

      await page.goto('/usage-logs');

      // Fresh login modal should appear
      await expect(page.getByText('Please Verify', {exact: true})).toBeVisible({
        timeout: 10000,
      });

      // Enter correct password and verify
      await page.getByPlaceholder('Current Password').fill('password');
      await page.getByRole('button', {name: 'Verify'}).click();

      // Modal should close after successful verification
      await expect(
        page.getByText('Please Verify', {exact: true}),
      ).not.toBeVisible({
        timeout: 5000,
      });

      // The page should have retried and loaded (no error alert)
      await expect(
        page.getByText('Invalid verification credentials'),
      ).not.toBeVisible();

      // Verify two calls were made (original + retry)
      expect(logsCallCount).toBe(2);
    });
  },
);
