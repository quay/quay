import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

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

    test('timestamps checkbox remains checked after initial load', async ({
      superuserPage,
    }) => {
      await superuserPage.goto('/build-logs');

      // Wait for loading to finish (spinner should disappear)
      await expect(superuserPage.getByLabel('Loading')).not.toBeVisible({
        timeout: 10_000,
      });

      const checkbox = superuserPage.getByTestId('show-timestamps-checkbox');
      await expect(checkbox).toBeVisible();
      await expect(checkbox).toBeChecked();
    });

    test('loads a triggerless build without 500 error', async ({
      superuserPage,
      superuserRequest,
      api,
    }) => {
      const org = await api.organization('sunotrigger');
      const repo = await api.repository(org.name, 'notrigger');
      const build = await api.build(org.name, repo.name);

      // API layer: verify the fix — trigger is null, not a 500
      const response = await superuserRequest.get(
        `${API_URL}/api/v1/superuser/${build.buildId}/build`,
      );
      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body).toHaveProperty('trigger', null);

      // UI layer: verify Build Logs page renders the build without crashing
      await superuserPage.goto('/build-logs');
      await superuserPage.getByTestId('build-uuid-input').fill(build.buildId);
      await superuserPage.getByTestId('load-build-button').click();

      await expect(superuserPage.getByText('Build Information')).toBeVisible({
        timeout: 30_000,
      });
      await expect(superuserPage.getByText(build.buildId)).toBeVisible();
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

      // Verify the fix: logs are rendered, not the empty state
      await expect(
        superuserPage.getByText('No logs available'),
      ).not.toBeVisible();
    });

    test('readonly superuser can view archived build logs without repo membership', async ({
      readonlyPage,
      readonlyContext,
      superuserApi,
    }) => {
      test.slow();
      test.setTimeout(300_000);

      // Create a private repo under a separate org — the readonly superuser
      // has no membership in this org, so /logarchive/<uuid> would 403.
      const org = await superuserApi.organization('roarchive');
      const repo = await superuserApi.repository(org.name, 'private-logs');

      const build = await superuserApi.build(
        org.name,
        repo.name,
        'FROM scratch\nLABEL test="readonly-archived-logs"\n',
      );

      await superuserApi.raw.waitForBuildPhase(
        org.name,
        repo.name,
        build.buildId,
      );

      // Wait for the build logs archiver to archive this build's logs.
      // The archiver polls every 30s and archives one build per cycle.
      const readonlyRequest = readonlyContext.request;
      const logsEndpoint = `${API_URL}/api/v1/superuser/${build.buildId}/logs`;
      const archiveDeadline = Date.now() + 120_000;
      let hasLogsUrl = false;
      while (Date.now() < archiveDeadline) {
        const resp = await readonlyRequest.get(logsEndpoint);
        if (resp.ok()) {
          const body = await resp.json();
          if (body.logs_url) {
            hasLogsUrl = true;
            break;
          }
        }
        await new Promise((r) => setTimeout(r, 5_000));
      }
      test.skip(!hasLogsUrl, 'Archiver did not archive logs within timeout');

      // Load Build Logs page as the readonly superuser — should render
      // archived logs via the superuser archive endpoint, not 403 from /logarchive/
      await readonlyPage.goto('/build-logs');
      await readonlyPage.getByTestId('build-uuid-input').fill(build.buildId);
      await readonlyPage.getByTestId('load-build-button').click();

      await expect(readonlyPage.getByText('Build Information')).toBeVisible({
        timeout: 30_000,
      });

      await expect(readonlyPage.getByTestId('build-logs-display')).toBeVisible({
        timeout: 15_000,
      });

      // The key assertion: no error alert and no empty state
      await expect(
        readonlyPage.getByTestId('build-error-alert'),
      ).not.toBeVisible();
      await expect(
        readonlyPage.getByText('No logs available'),
      ).not.toBeVisible();
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
