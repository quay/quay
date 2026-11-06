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

    await expect(authenticatedPage.locator('.about-page')).toBeVisible();
    await expect(
      authenticatedPage.getByRole('heading', {name: 'Founded'}),
    ).toBeVisible();
    await expect(
      authenticatedPage.getByText('New York City, NY'),
    ).toBeVisible();
  });
});
