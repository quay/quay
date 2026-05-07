import {test, expect} from '@playwright/test';

test.describe('UI Toggle', {tag: ['@legacy-ui', '@smoke']}, () => {
  test('visiting /angular sets cookie and loads Angular UI', async ({page}) => {
    await page.goto('/angular', {waitUntil: 'domcontentloaded'});

    const cookies = await page.context().cookies();
    const uiCookie = cookies.find((c) => c.name === 'defaultui');
    expect(uiCookie?.value).toBe('angular');

    await expect(page.locator('html[ng-app="quay"]')).toBeAttached({
      timeout: 15000,
    });
  });

  test('visiting /react sets cookie and loads React UI', async ({page}) => {
    await page.goto('/react', {waitUntil: 'domcontentloaded'});

    const cookies = await page.context().cookies();
    const uiCookie = cookies.find((c) => c.name === 'defaultui');
    expect(uiCookie?.value).toBe('react');

    await expect(page.locator('#root')).toBeAttached({timeout: 15000});
    await expect(page.locator('html[ng-app="quay"]')).not.toBeAttached();
  });

  test('toggling from React to Angular and back', async ({page}) => {
    await page.goto('/react', {waitUntil: 'domcontentloaded'});
    await expect(page.locator('#root')).toBeAttached({timeout: 15000});

    // /angular sets cookie and redirects to /. Reload to ensure nginx
    // re-evaluates the cookie and serves Angular instead of cached React.
    await page.goto('/angular', {waitUntil: 'domcontentloaded'});
    await page.reload({waitUntil: 'domcontentloaded'});
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached({
      timeout: 15000,
    });

    await page.goto('/react', {waitUntil: 'domcontentloaded'});
    await page.reload({waitUntil: 'domcontentloaded'});
    await expect(page.locator('#root')).toBeAttached({timeout: 15000});
    await expect(page.locator('html[ng-app="quay"]')).not.toBeAttached();
  });

  test('cookie persists across navigations', async ({page}) => {
    await page.goto('/angular', {waitUntil: 'domcontentloaded'});

    await page.goto('/', {waitUntil: 'domcontentloaded'});
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached({
      timeout: 15000,
    });

    const cookies = await page.context().cookies();
    const uiCookie = cookies.find((c) => c.name === 'defaultui');
    expect(uiCookie?.value).toBe('angular');
  });
});
