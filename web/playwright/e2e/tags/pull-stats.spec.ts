import {test, expect, getTestUsers} from '../../fixtures';
import {pushImage} from '../../utils/container';

test.describe('Tags - Pull Statistics', {tag: ['@tags', '@PROJQUAY-10095']}, () => {
  test('hides pull stats columns when IMAGE_PULL_STATS is disabled', async ({
    authenticatedPage,
    api,
    quayConfig,
  }) => {
    test.skip(
      quayConfig.features?.IMAGE_PULL_STATS === true,
      'IMAGE_PULL_STATS is enabled in this environment',
    );

    const repo = await api.repository();
    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

    await expect(
      authenticatedPage.getByRole('columnheader', {name: 'Last Pulled'}),
    ).not.toBeVisible();
    await expect(
      authenticatedPage.getByRole('columnheader', {name: 'Pull Count'}),
    ).not.toBeVisible();
  });

  test.describe(
    'when IMAGE_PULL_STATS is enabled',
    {tag: ['@feature:IMAGE_PULL_STATS', '@container']},
    () => {
      test.slow();

      test('shows Last Pulled and Pull Count columns on the Tags page', async ({
        authenticatedPage,
        api,
        quayConfig,
      }) => {
        const users = getTestUsers(quayConfig);
        const repo = await api.repository();
        await pushImage(
          repo.namespace,
          repo.name,
          'latest',
          users.user.username,
          users.user.password,
        );

        await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);
        await expect(
          authenticatedPage.getByRole('link', {name: 'latest'}),
        ).toBeVisible({timeout: 30000});

        await expect(
          authenticatedPage.getByRole('columnheader', {name: 'Last Pulled'}),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByRole('columnheader', {name: 'Pull Count'}),
        ).toBeVisible();

        const tagRow = authenticatedPage.getByRole('row').filter({
          has: authenticatedPage.getByRole('link', {name: 'latest'}),
        });
        // No pulls yet (or flush pending) — UI shows Never / 0 defaults.
        await expect(tagRow.getByText('Never')).toBeVisible();
        await expect(tagRow.getByText('0', {exact: true})).toBeVisible();
      });
    },
  );
});
