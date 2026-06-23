import {test, expect} from '../../fixtures';

test.describe(
  'Superuser Build Logs',
  {tag: ['@superuser', '@feature:BUILD_SUPPORT']},
  () => {
    test('denies access to non-superusers', async ({authenticatedPage}) => {
      await authenticatedPage.goto('/build-logs');

      await expect(authenticatedPage.getByText('Access Denied')).toBeVisible();
      await expect(
        authenticatedPage.getByText(
          'You must be a superuser to access build logs',
        ),
      ).toBeVisible();
    });

    test('superuser can access build logs page', async ({superuserPage}) => {
      await superuserPage.goto('/build-logs');

      await expect(
        superuserPage.getByRole('heading', {name: 'Build Logs', level: 1}),
      ).toBeVisible();
      await expect(superuserPage.getByTestId('build-uuid-input')).toBeVisible();
      await expect(
        superuserPage.getByTestId('show-timestamps-checkbox'),
      ).toBeVisible();
      await expect(
        superuserPage.getByTestId('load-build-button'),
      ).toBeVisible();
      await expect(superuserPage.getByTestId('build-logs-nav')).toBeVisible();
    });

    test('disables load button when input is empty', async ({
      superuserPage,
    }) => {
      await superuserPage.goto('/build-logs');

      await expect(
        superuserPage.getByTestId('load-build-button'),
      ).toBeDisabled();

      await superuserPage.getByTestId('build-uuid-input').fill('some-uuid');
      await expect(
        superuserPage.getByTestId('load-build-button'),
      ).toBeEnabled();

      await superuserPage.getByTestId('build-uuid-input').fill('');
      await expect(
        superuserPage.getByTestId('load-build-button'),
      ).toBeDisabled();
    });

    test('shows error for invalid build UUID', async ({superuserPage}) => {
      await superuserPage.goto('/build-logs');

      await superuserPage
        .getByTestId('build-uuid-input')
        .fill('invalid-uuid-does-not-exist');
      await superuserPage.getByTestId('load-build-button').click();

      await expect(
        superuserPage.getByTestId('build-error-alert'),
      ).toBeVisible();
      await expect(
        superuserPage.getByText('Cannot find or load build'),
      ).toBeVisible();
    });

    test('timestamps checkbox defaults to checked', async ({superuserPage}) => {
      await superuserPage.goto('/build-logs');

      const checkbox = superuserPage.getByTestId('show-timestamps-checkbox');
      await expect(checkbox).toBeChecked();

      await checkbox.click();
      await expect(checkbox).not.toBeChecked();

      await checkbox.click();
      await expect(checkbox).toBeChecked();
    });

    test('displays archived build logs fetched via logs_url', async ({
      superuserPage,
      api,
    }) => {
      const org = await api.organization('suarchive');
      const repo = await api.repository(org.name, 'archived');
      const build = await api.build(org.name, repo.name);

      const archivedLogs = {
        start: 0,
        total: 3,
        logs: [
          {type: 'phase', message: 'pulling'},
          {type: 'command', message: 'FROM scratch'},
          {type: 'phase', message: 'complete'},
        ],
      };

      // Mock the logs endpoint to return logs_url (simulating archived logs)
      await superuserPage.route(
        `**/api/v1/superuser/${build.buildId}/logs`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              logs_url: `http://fake-archive.example.com/buildlogs/${build.buildId}`,
            }),
          });
        },
      );

      // Mock the archive URL to return actual log entries
      await superuserPage.route(
        `**/buildlogs/${build.buildId}`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(archivedLogs),
          });
        },
      );

      await superuserPage.goto('/build-logs');
      await superuserPage.getByTestId('build-uuid-input').fill(build.buildId);
      await superuserPage.getByTestId('load-build-button').click();

      await expect(superuserPage.getByText('Build Information')).toBeVisible({
        timeout: 30_000,
      });

      // Verify logs are displayed (not "No logs available")
      await expect(superuserPage.getByTestId('build-logs-display')).toBeVisible(
        {timeout: 15_000},
      );
      await expect(
        superuserPage.getByText('No logs available'),
      ).not.toBeVisible();
      await expect(superuserPage.getByText('FROM scratch')).toBeVisible();
    });

    test('loads and displays real build logs', async ({
      superuserPage,
      superuserApi,
      api,
    }) => {
      test.setTimeout(180_000);

      const org = await api.organization('sulogs');
      const repo = await api.repository(org.name, 'build-logs');

      const build = await api.build(
        org.name,
        repo.name,
        'FROM scratch\nLABEL test="superuser-logs"\n',
      );

      await api.raw.waitForBuildPhase(org.name, repo.name, build.buildId);

      // Re-sign in to refresh the superuser session (stales during build wait)
      await superuserApi.raw.signIn('admin', 'password');

      await superuserPage.goto('/build-logs');

      await superuserPage.getByTestId('build-uuid-input').fill(build.buildId);
      await superuserPage.getByTestId('load-build-button').click();

      await expect(superuserPage.getByText('Build Information')).toBeVisible({
        timeout: 30_000,
      });
      await expect(superuserPage.getByText(build.buildId)).toBeVisible();

      await expect(superuserPage.getByTestId('build-logs-display')).toBeVisible(
        {timeout: 15_000},
      );
    });

    test('navigates to Build Logs via sidebar', async ({superuserPage}) => {
      await superuserPage.goto('/organization');

      const superuserNavSection = superuserPage.getByRole('button', {
        name: 'Superuser',
      });
      await superuserNavSection.click();

      await superuserPage.getByTestId('build-logs-nav').click();

      await expect(superuserPage).toHaveURL(/.*\/build-logs.*/);
      await expect(
        superuserPage.getByRole('heading', {name: 'Build Logs'}),
      ).toBeVisible();
      await expect(superuserPage.getByTestId('build-uuid-input')).toBeVisible();
    });
  },
);

test.describe(
  'Superuser Build Logs - BUILD_SUPPORT disabled',
  {tag: ['@superuser', '@feature:SUPERUSERS_FULL_ACCESS']},
  () => {
    test('shows warning when BUILD_SUPPORT is disabled', async ({
      superuserPage,
      quayConfig,
    }) => {
      test.skip(
        quayConfig?.features?.BUILD_SUPPORT === true,
        'BUILD_SUPPORT is enabled',
      );

      await superuserPage.goto('/build-logs');

      await expect(
        superuserPage.getByText('Build support not enabled'),
      ).toBeVisible();
      await expect(
        superuserPage.getByText(
          'BUILD_SUPPORT is not enabled in the registry configuration',
        ),
      ).toBeVisible();
    });

    test('hides Build Logs in sidebar when BUILD_SUPPORT is disabled', async ({
      superuserPage,
      quayConfig,
    }) => {
      test.skip(
        quayConfig?.features?.BUILD_SUPPORT === true,
        'BUILD_SUPPORT is enabled',
      );

      await superuserPage.goto('/organization');

      const superuserNavSection = superuserPage.getByRole('button', {
        name: 'Superuser',
      });
      await superuserNavSection.click();

      await expect(
        superuserPage.getByTestId('build-logs-nav'),
      ).not.toBeVisible();
    });
  },
);
