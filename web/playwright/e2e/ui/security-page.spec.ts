import {test, expect} from '../../fixtures';

test.describe('Security Page', {tag: ['@ui']}, () => {
  test('renders security heading and introduction', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/security');

    await expect(
      authenticatedPage.getByRole('heading', {name: 'Quay Security'}),
    ).toBeVisible();

    await expect(
      authenticatedPage.getByText(
        'We understand that when you upload one of your repositories',
        {exact: false},
      ),
    ).toBeVisible();
  });

  test('renders all security sections', async ({authenticatedPage}) => {
    await authenticatedPage.goto('/security');

    await expect(
      authenticatedPage.getByRole('heading', {name: 'SSL Everywhere'}),
    ).toBeVisible();
    await expect(
      authenticatedPage.getByRole('heading', {name: 'Encryption'}),
    ).toBeVisible();
    await expect(
      authenticatedPage.getByRole('heading', {name: 'Passwords'}),
    ).toBeVisible();
    await expect(
      authenticatedPage.getByRole('heading', {name: 'Access Controls'}),
    ).toBeVisible();
    await expect(
      authenticatedPage.getByRole('heading', {name: 'Firewalls'}),
    ).toBeVisible();
    await expect(
      authenticatedPage.getByRole('heading', {name: 'Data Resilience'}),
    ).toBeVisible();
  });
});
