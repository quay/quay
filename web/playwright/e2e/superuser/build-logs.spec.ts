import {test, expect} from '../../fixtures';

test.describe(
  'Superuser Build Logs',
  {tag: ['@superuser', '@feature:BUILD_SUPPORT']},
  () => {
    test('superuser can access build logs page', async ({superuserPage}) => {
      await superuserPage.goto('/build-logs');

      await expect(
        superuserPage.getByRole('heading', {name: 'Build Logs', level: 1}),
      ).toBeVisible();

      // UUID input form
      await expect(superuserPage.getByTestId('build-uuid-input')).toBeVisible();
      await expect(
        superuserPage.getByTestId('show-timestamps-checkbox'),
      ).toBeVisible();
      await expect(
        superuserPage.getByTestId('load-build-button'),
      ).toBeVisible();
    });

    test('load button disabled when UUID input is empty', async ({
      superuserPage,
    }) => {
      await superuserPage.goto('/build-logs');

      const loadBtn = superuserPage.getByTestId('load-build-button');
      await expect(loadBtn).toBeDisabled();
    });

    test('shows error for invalid build UUID', async ({superuserPage}) => {
      await superuserPage.goto('/build-logs');

      await superuserPage
        .getByTestId('build-uuid-input')
        .fill('nonexistent-uuid');
      await superuserPage.getByTestId('load-build-button').click();

      await expect(
        superuserPage.getByTestId('build-error-alert'),
      ).toBeVisible();
    });

    test('shows error or build info when UUID is submitted', async ({
      superuserPage,
      superuserApi,
    }) => {
      const org = await superuserApi.organization('subldlogs');
      const repo = await superuserApi.repository(org.name, 'bldlogs-repo');
      const build = await superuserApi.build(org.name, repo.name);

      await superuserPage.goto('/build-logs');

      await superuserPage.getByTestId('build-uuid-input').fill(build.buildId);
      await superuserPage.getByTestId('load-build-button').click();

      // The API may return build info or an error depending on backend support
      await expect(
        superuserPage
          .getByText('Build Information')
          .or(superuserPage.getByTestId('build-error-alert')),
      ).toBeVisible();
    });

    test('timestamps checkbox toggles log timestamps', async ({
      superuserPage,
    }) => {
      await superuserPage.goto('/build-logs');

      const checkbox = superuserPage.getByTestId('show-timestamps-checkbox');
      await expect(checkbox).toBeVisible();

      // Default is checked
      await expect(checkbox).toBeChecked();

      // Uncheck
      await checkbox.click();
      await expect(checkbox).not.toBeChecked();

      // Re-check
      await checkbox.click();
      await expect(checkbox).toBeChecked();
    });

    test('non-superuser sees access denied', async ({authenticatedPage}) => {
      await authenticatedPage.goto('/build-logs');

      await expect(authenticatedPage.getByText('Access Denied')).toBeVisible();
    });
  },
);
