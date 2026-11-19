import {test, expect} from '../../fixtures';

test.describe('OAuth Local Handler', {tag: ['@auth']}, () => {
  test('format=json renders token as plain text content', async ({
    unauthenticatedPage: page,
  }) => {
    const testToken = 'test-token-value';
    await page.goto(`/oauth/localapp?format=json#access_token=${testToken}`);

    const bodyText = await page.evaluate(() => document.body.textContent);
    expect(bodyText).toBe(JSON.stringify({access_token: testToken}));
  });

  test('format=json does not render HTML in token value', async ({
    unauthenticatedPage: page,
  }) => {
    const xssPayload = '<img src=x onerror=alert(1)>';
    await page.goto(
      `/oauth/localapp?format=json#access_token=${encodeURIComponent(xssPayload)}`,
    );

    const bodyText = await page.evaluate(() => document.body.textContent);
    expect(bodyText).toBe(JSON.stringify({access_token: xssPayload}));

    const imgCount = await page.evaluate(
      () => document.querySelectorAll('img[src="x"]').length,
    );
    expect(imgCount).toBe(0);
  });

  test('displays cancellation message when no hash is present', async ({
    unauthenticatedPage: page,
  }) => {
    await page.goto('/oauth/localapp');

    await expect(page.getByText('Authorization was cancelled')).toBeVisible();
  });
});
