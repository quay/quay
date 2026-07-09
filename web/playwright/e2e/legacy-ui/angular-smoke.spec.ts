import {test, expect} from '@playwright/test';
import {API_URL} from '../../utils/config';
import {TEST_USERS} from '../../global-setup';

test.describe('Angular UI Smoke Tests', {tag: ['@legacy-ui', '@smoke']}, () => {
  test.beforeEach(async ({page}) => {
    await page.goto('/angular', {waitUntil: 'domcontentloaded'});
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached({
      timeout: 15000,
    });
  });

  test('sign-in page renders', {tag: '@service-safe'}, async ({page}) => {
    await page.goto('/signin/', {waitUntil: 'domcontentloaded'});
    await expect(page.locator('body')).toContainText(
      /Sign in|Log in to your (Red Hat )?account|Red Hat login/i,
    );
  });

  test('repository list page loads after login', async ({page, request}) => {
    // Log in via API to get session cookies
    const csrfResponse = await request.get(`${API_URL}/csrf_token`);
    expect(csrfResponse.ok()).toBeTruthy();
    const csrfData = await csrfResponse.json();

    const signinResponse = await request.post(`${API_URL}/api/v1/signin`, {
      headers: {'X-CSRF-Token': csrfData.csrf_token},
      data: {
        username: TEST_USERS.admin.username,
        password: TEST_USERS.admin.password,
      },
    });
    expect(signinResponse.ok()).toBeTruthy();

    // Transfer cookies from API context to the browser page
    const cookies = await request.storageState();
    await page.context().addCookies(cookies.cookies);

    // Derive domain from the baseURL so tests work in any environment
    const baseUrl = new URL(
      page.context().pages()[0]?.url() || 'http://localhost:8080',
    );
    await page.context().addCookies([
      {
        name: 'defaultui',
        value: 'angular',
        domain: baseUrl.hostname,
        path: '/',
      },
    ]);

    await page.goto('/repository/', {waitUntil: 'domcontentloaded'});
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached();

    // Verify Angular routed to a page (ng-view has rendered content).
    // After first login Angular may redirect to /updateuser for profile
    // prompts, so accept any ng-view content as success.
    await expect(page.locator('[ng-view] > *').first()).toBeAttached({
      timeout: 15000,
    });
  });

  test('about page loads', {tag: '@service-safe'}, async ({page}) => {
    await page.goto('/about/', {waitUntil: 'domcontentloaded'});
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached();
  });

  test(
    'API health endpoint is reachable through nginx',
    {tag: '@service-safe'},
    async ({request}) => {
      const response = await request.get('/health/instance');
      expect(response.ok()).toBeTruthy();
    },
  );

  test(
    'API config endpoint returns expected fields',
    {tag: '@service-safe'},
    async ({request}) => {
      const response = await request.get(`${API_URL}/config`);
      expect(response.ok()).toBeTruthy();
      const config = await response.json();
      expect(config).toHaveProperty('features');
      expect(config).toHaveProperty('config');
    },
  );
});
