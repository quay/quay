import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';
import {expectSigninPageForTarget} from '../../utils/signin';

test.describe('Service-safe smoke', {tag: ['@service-safe', '@ui']}, () => {
  test('signin page renders without authentication', async ({
    unauthenticatedPage,
  }) => {
    await unauthenticatedPage.goto('/signin');

    await expectSigninPageForTarget(unauthenticatedPage);
  });

  test('public config endpoint is readable', async ({request}) => {
    const response = await request.get(`${API_URL}/config`);

    expect(response.ok()).toBe(true);
    const body = await response.json();
    expect(body.config?.SERVER_HOSTNAME).toBeTruthy();
  });
});
