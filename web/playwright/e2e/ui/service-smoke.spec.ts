import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

test.describe('Service-safe smoke', {tag: ['@service-safe', '@ui']}, () => {
  test('signin page renders without authentication', async ({
    unauthenticatedPage,
  }) => {
    await unauthenticatedPage.goto('/signin');

    await expect(unauthenticatedPage.locator('body')).toBeVisible();
    await expect(unauthenticatedPage.locator('body')).toContainText(
      /Log in to your (Red Hat )?account|Red Hat login/i,
    );
  });

  test('public config endpoint is readable', async ({request}) => {
    const response = await request.get(`${API_URL}/config`);

    expect(response.ok()).toBe(true);
    const body = await response.json();
    expect(body.config?.SERVER_HOSTNAME).toBeTruthy();
  });
});
