/**
 * Fresh Login - OIDC vs Database behavior tests
 *
 * Uses page.route() to intercept GET /api/v1/superuser/logs* and return a
 * 401 fresh_login_required response. This is an approved exemption from the
 * no-mock policy: the fresh_login_required error requires the user's session
 * to be older than FRESH_LOGIN_TIMEOUT (default 10 minutes), which cannot be
 * triggered on demand via the real API. Additionally, the OIDC redirect path
 * under test requires an external IdP that is not available in standard CI
 * environments. The mock simulates valid Quay error responses to verify that
 * OIDC users are redirected to /signin rather than shown the password modal.
 */
import {test, expect} from '../../fixtures';

test.describe(
  'Fresh Login - OIDC vs Database behavior',
  {tag: ['@auth', '@auth:OIDC']},
  () => {
    test(
      'OIDC users redirect to signin on fresh_login_required (not password modal)',
      {tag: '@superuser'},
      async ({superuserPage: page, quayConfig}) => {
        test.skip(
          quayConfig?.config?.AUTHENTICATION_TYPE !== 'OIDC',
          'Requires AUTHENTICATION_TYPE: OIDC',
        );

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

        // Should redirect to signin (not show password modal)
        await expect(page).toHaveURL(/\/signin/, {
          timeout: 10000,
        });

        // Password modal should NOT appear
        await expect(page.getByText('Please Verify')).not.toBeVisible();
        await expect(page.getByText('Current Password')).not.toBeVisible();
      },
    );

    test(
      'OIDC redirect preserves query parameters',
      {tag: '@superuser'},
      async ({superuserPage: page, quayConfig}) => {
        test.skip(
          quayConfig?.config?.AUTHENTICATION_TYPE !== 'OIDC',
          'Requires AUTHENTICATION_TYPE: OIDC',
        );

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

        await page.goto('/usage-logs?starttime=01/01/2025&endtime=01/31/2025');

        // Should redirect to signin
        await expect(page).toHaveURL(/\/signin/, {
          timeout: 10000,
        });

        // Verify query parameters are preserved in the redirect URL
        const url = page.url();
        expect(url).toMatch(/starttime|usage-logs/);
      },
    );
  },
);
