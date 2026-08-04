import {test, expect} from '../../fixtures';

test.describe('Help menu', {tag: ['@ui']}, () => {
  test('renders help menu toggle in the masthead', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/organization');
    const toggle = authenticatedPage.getByTestId('help-menu-toggle');
    await expect(toggle).toBeVisible();
  });

  test('opens dropdown and shows documentation links', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/organization');
    const toggle = authenticatedPage.getByTestId('help-menu-toggle');
    await toggle.click();

    const docLink = authenticatedPage.getByTestId('help-documentation-link');
    await expect(docLink).toBeVisible();
    await expect(docLink).toContainText('Documentation');

    const apiLink = authenticatedPage.getByTestId('help-api-reference-link');
    await expect(apiLink).toBeVisible();
    await expect(apiLink).toContainText('API Reference');
  });

  test('shows version info when available', async ({
    authenticatedPage,
    quayConfig,
  }) => {
    test.skip(!quayConfig?.version_number, 'No version_number in config');

    await authenticatedPage.goto('/organization');
    const toggle = authenticatedPage.getByTestId('help-menu-toggle');
    await toggle.click();

    const versionItem = authenticatedPage.getByTestId('help-version-info');
    await expect(versionItem).toBeVisible();
    await expect(versionItem).not.toHaveText('');
  });

  test('closes dropdown when clicking toggle again', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/organization');
    const toggle = authenticatedPage.getByTestId('help-menu-toggle');

    await toggle.click();
    await expect(
      authenticatedPage.getByTestId('help-documentation-link'),
    ).toBeVisible();

    await toggle.click();
    await expect(
      authenticatedPage.getByTestId('help-documentation-link'),
    ).not.toBeVisible();
  });
});
