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
    // networkidle lets React finish its async auth-check redirect cycle
    // (API call → 401 → /signin) before we navigate away, preventing
    // ERR_ABORTED races and stale cache responses on the next goto.
    await page.goto('/react', {waitUntil: 'networkidle'});
    await expect(page.locator('#root')).toBeAttached({timeout: 15000});

    // /angular sets cookie and redirects to /. The redirected page may
    // serve cached React HTML; networkidle lets it settle, then reload
    // forces nginx to re-evaluate the cookie and proxy to Flask/Angular.
    await page.goto('/angular', {waitUntil: 'networkidle'});
    await page.reload({waitUntil: 'networkidle'});
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached({
      timeout: 15000,
    });

    await page.goto('/react', {waitUntil: 'networkidle'});
    await page.reload({waitUntil: 'networkidle'});
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
