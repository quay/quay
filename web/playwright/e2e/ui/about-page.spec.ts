import {test, expect} from '../../fixtures';

test.describe('About Page', {tag: ['@ui']}, () => {
  test('renders About Us heading and sections', async ({authenticatedPage}) => {
    await authenticatedPage.goto('/about');

    await expect(
      authenticatedPage.getByRole('heading', {name: 'About Us'}),
    ).toBeVisible();
  });

  test('displays company information cards', async ({authenticatedPage}) => {
    await authenticatedPage.goto('/about');

    // TheBasics component renders company history cards
    await expect(authenticatedPage.locator('.about-page')).toBeVisible();
  });

  test('displays packages table', async ({authenticatedPage}) => {
    await authenticatedPage.goto('/about');

    // PackagesTable renders as a PF grid with packages data
    await expect(
      authenticatedPage.getByRole('grid', {
        name: 'Packages and projects table',
      }),
    ).toBeVisible();
  });
});
