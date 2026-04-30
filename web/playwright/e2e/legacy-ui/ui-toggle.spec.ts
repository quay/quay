import {test, expect} from '@playwright/test';

test.describe('UI Toggle', {tag: ['@legacy-ui', '@smoke']}, () => {
  test('visiting /angular sets cookie and loads Angular UI', async ({page}) => {
    await page.goto('/angular');
    await page.waitForLoadState('domcontentloaded');

    const cookies = await page.context().cookies();
    const uiCookie = cookies.find((c) => c.name === 'defaultui');
    expect(uiCookie?.value).toBe('angular');

    // Angular UI renders with ng-app="quay" on the html element
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached({
      timeout: 15000,
    });
  });

  test('visiting /react sets cookie and loads React UI', async ({page}) => {
    await page.goto('/react');
    await page.waitForLoadState('domcontentloaded');

    const cookies = await page.context().cookies();
    const uiCookie = cookies.find((c) => c.name === 'defaultui');
    expect(uiCookie?.value).toBe('react');

    // React UI serves from patternfly index.html with a #root mount point
    await expect(page.locator('#root')).toBeAttached({timeout: 15000});
    // Angular's ng-app attribute should NOT be present
    await expect(page.locator('html[ng-app="quay"]')).not.toBeAttached();
  });

  test('toggling from React to Angular and back', async ({page}) => {
    // Start with React
    await page.goto('/react');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('#root')).toBeAttached({timeout: 15000});

    // Switch to Angular
    await page.goto('/angular');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached({
      timeout: 15000,
    });

    // Switch back to React
    await page.goto('/react');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('#root')).toBeAttached({timeout: 15000});
    await expect(page.locator('html[ng-app="quay"]')).not.toBeAttached();
  });

  test('cookie persists across navigations', async ({page}) => {
    // Set Angular cookie
    await page.goto('/angular');
    await page.waitForLoadState('domcontentloaded');

    // Navigate to root — should still be Angular
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('html[ng-app="quay"]')).toBeAttached({
      timeout: 15000,
    });

    const cookies = await page.context().cookies();
    const uiCookie = cookies.find((c) => c.name === 'defaultui');
    expect(uiCookie?.value).toBe('angular');
  });
});
