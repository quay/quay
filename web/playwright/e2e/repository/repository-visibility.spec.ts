import {test, expect} from '../../fixtures';

test.describe(
  'Repository Visibility',
  {tag: ['@repository', '@settings']},
  () => {
    test('changes visibility from private to public', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository(undefined, 'visrepo', 'private');

      await authenticatedPage.goto(
        `/repository/${repo.namespace}/${repo.name}?tab=settings`,
      );
      await authenticatedPage
        .getByTestId('settings-tab-repositoryvisiblity')
        .click();

      await expect(
        authenticatedPage.getByTestId('visibility-private-description'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('visibility-make-public-btn'),
      ).toBeVisible();

      await authenticatedPage.getByTestId('visibility-make-public-btn').click();

      await expect(
        authenticatedPage.getByTestId('visibility-public-description'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('visibility-make-private-btn'),
      ).toBeVisible();
    });

    test('changes visibility from public to private', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository(undefined, 'visrepo', 'public');

      await authenticatedPage.goto(
        `/repository/${repo.namespace}/${repo.name}?tab=settings`,
      );
      await authenticatedPage
        .getByTestId('settings-tab-repositoryvisiblity')
        .click();

      await expect(
        authenticatedPage.getByTestId('visibility-public-description'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('visibility-make-private-btn'),
      ).toBeVisible();

      await authenticatedPage
        .getByTestId('visibility-make-private-btn')
        .click();

      await expect(
        authenticatedPage.getByTestId('visibility-private-description'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('visibility-make-public-btn'),
      ).toBeVisible();
    });
  },
);
