import {test, expect} from '../../fixtures';

test.describe('Theme Switcher', {tag: ['@ui']}, () => {
  test('theme toggle buttons exist and auto is default', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/overview');

    // Verify default is light (no dark class)
    await expect(authenticatedPage.locator('html')).not.toHaveClass(
      /pf-v5-theme-dark/,
    );

    // Open user menu
    await authenticatedPage.getByTestId('user-menu-toggle').click();

    // Verify all theme buttons exist (use buttonId to target actual button elements)
    await expect(
      authenticatedPage.locator('#toggle-group-light-theme'),
    ).toBeVisible();
    await expect(
      authenticatedPage.locator('#toggle-group-dark-theme'),
    ).toBeVisible();
    await expect(
      authenticatedPage.locator('#toggle-group-auto-theme'),
    ).toBeVisible();

    // Verify auto is selected by default (pf-m-selected is on the button element)
    await expect(
      authenticatedPage.locator('#toggle-group-auto-theme'),
    ).toHaveClass(/pf-m-selected/);
  });

  test('switches between themes with localStorage persistence', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/overview');

    // Open menu and switch to dark
    await authenticatedPage.getByTestId('user-menu-toggle').click();
    await authenticatedPage.locator('#toggle-group-dark-theme').click();

    // Verify dark theme applied
    await expect(authenticatedPage.locator('html')).toHaveClass(
      /pf-v5-theme-dark/,
    );

    // Verify localStorage
    const darkPref = await authenticatedPage.evaluate(() =>
      localStorage.getItem('theme-preference'),
    );
    expect(darkPref).toBe('DARK');

    // Reload and verify persistence
    await authenticatedPage.reload();
    await expect(authenticatedPage.locator('html')).toHaveClass(
      /pf-v5-theme-dark/,
    );

    // Switch to light
    await authenticatedPage.getByTestId('user-menu-toggle').click();
    await authenticatedPage.locator('#toggle-group-light-theme').click();

    // Verify light theme
    await expect(authenticatedPage.locator('html')).not.toHaveClass(
      /pf-v5-theme-dark/,
    );
    const lightPref = await authenticatedPage.evaluate(() =>
      localStorage.getItem('theme-preference'),
    );
    expect(lightPref).toBe('LIGHT');
  });

  test('auto theme respects browser color scheme preference', async ({
    authenticatedPage,
  }) => {
    // Emulate dark mode preference
    await authenticatedPage.emulateMedia({colorScheme: 'dark'});
    await authenticatedPage.goto('/overview');

    // With auto theme (default), should show dark
    await expect(authenticatedPage.locator('html')).toHaveClass(
      /pf-v5-theme-dark/,
    );

    // Verify auto is still selected
    await authenticatedPage.getByTestId('user-menu-toggle').click();
    await expect(
      authenticatedPage.locator('#toggle-group-auto-theme'),
    ).toHaveClass(/pf-m-selected/);

    // Switch to light preference - verify reactive change
    await authenticatedPage.emulateMedia({colorScheme: 'light'});
    await expect(authenticatedPage.locator('html')).not.toHaveClass(
      /pf-v5-theme-dark/,
    );
  });
});
