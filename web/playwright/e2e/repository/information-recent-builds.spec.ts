import {test, expect} from '../../fixtures';

test.describe(
  'Repository Information - Recent Builds',
  {tag: ['@repository', '@feature:BUILD_SUPPORT']},
  () => {
    test('displays Recent Repo Builds section when builds exist', async ({
      authenticatedPage,
      api,
    }) => {
      // Create test organization with repository
      const org = await api.organization('recentbuilds');
      const repo = await api.repository(org.name, 'test-repo');

      // Create a build so the Recent Repo Builds section shows builds
      await api.build(org.name, repo.name);

      // Navigate to repository Information tab
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=information`,
      );

      // Verify Recent Repo Builds card is visible
      await expect(
        authenticatedPage.getByText('Recent Repo Builds'),
      ).toBeVisible();
    });

    test('displays empty state when no builds exist', async ({
      authenticatedPage,
      api,
    }) => {
      // Create test organization with empty repository
      const org = await api.organization('nobuilds');
      const repo = await api.repository(org.name, 'empty-repo');

      // Navigate to repository Information tab
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=information`,
      );

      // Verify empty state message is shown
      await expect(
        authenticatedPage.getByText(
          'No builds have been run for this repository.',
        ),
      ).toBeVisible();

      // Verify guidance text for users with write access
      await expect(
        authenticatedPage.getByText(
          'Click on the Builds tab to start a new build.',
        ),
      ).toBeVisible();
    });

    test('displays View Build History link when builds exist', async ({
      authenticatedPage,
      api,
    }) => {
      // Create test organization with repository
      const org = await api.organization('adminbuilds');
      const repo = await api.repository(org.name, 'admin-repo');

      // Create a build so the View Build History link appears
      await api.build(org.name, repo.name);

      // Navigate to repository Information tab
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=information`,
      );

      // Verify View Build History link is visible (only shown when builds exist)
      await expect(
        authenticatedPage.getByRole('link', {name: 'View Build History'}),
      ).toBeVisible();
    });

    test('View Build History link navigates to Builds tab', async ({
      authenticatedPage,
      api,
    }) => {
      // Create test organization with repository
      const org = await api.organization('buildhistory');
      const repo = await api.repository(org.name, 'history-repo');

      // Create a build so the View Build History link appears
      await api.build(org.name, repo.name);

      // Navigate to repository Information tab
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=information`,
      );

      // Click on View Build History link
      await authenticatedPage
        .getByRole('link', {name: 'View Build History'})
        .click();

      // Verify navigation to Builds tab
      await expect(authenticatedPage).toHaveURL(
        new RegExp(`/repository/${org.name}/${repo.name}.*tab=builds`),
      );

      // Verify Builds tab is selected
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Builds', selected: true}),
      ).toBeVisible();
    });
  },
);
