import {test, expect} from '@playwright/test';
import {API_URL} from '../../utils/config';
import {TEST_USERS} from '../../global-setup';

test.describe('Angular UI Smoke Tests', {tag: ['@legacy-ui', '@smoke']}, () => {
  test.beforeEach(async ({page}) => {
    // Switch to Angular UI via nginx cookie
    await page.goto('/angular');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached({
      timeout: 15000,
    });
  });

  test('sign-in page renders', async ({page}) => {
    await page.goto('/signin/');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached();
    // Angular signin page has a form with username/password inputs
    await expect(page.locator('input[name="username"]')).toBeVisible({
      timeout: 10000,
    });
  });

  test('repository list page loads after login', async ({page, request}) => {
    // Log in via API to get session cookies
    const csrfResponse = await request.get(`${API_URL}/csrf_token`);
    const csrfData = await csrfResponse.json();

    await request.post(`${API_URL}/api/v1/signin`, {
      headers: {'X-CSRF-Token': csrfData.csrf_token},
      data: {
        username: TEST_USERS.admin.username,
        password: TEST_USERS.admin.password,
      },
    });

    // Transfer cookies from API context to the browser page
    const cookies = await request.storageState();
    await page.context().addCookies(cookies.cookies);

    // Ensure Angular cookie is still set
    await page.context().addCookies([
      {
        name: 'defaultui',
        value: 'angular',
        domain: 'localhost',
        path: '/',
      },
    ]);

    await page.goto('/repository/');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached();

    // The Angular repo list page renders with the quay-page class
    await expect(page.locator('.page-content')).toBeVisible({
      timeout: 15000,
    });
  });

  test('about page loads', async ({page}) => {
    await page.goto('/about/');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached();
  });

  test('API health endpoint is reachable through nginx', async ({request}) => {
    const response = await request.get('/health/instance');
    expect(response.ok()).toBeTruthy();
  });

  test('API config endpoint returns expected fields', async ({request}) => {
    const response = await request.get(`${API_URL}/config`);
    expect(response.ok()).toBeTruthy();
    const config = await response.json();
    expect(config).toHaveProperty('features');
    expect(config).toHaveProperty('config');
  });
});
