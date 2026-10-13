/**
 * Repository Mirroring E2E Tests
 *
 * Tests for repository mirroring functionality including:
 * - Feature flag behavior and tab visibility
 * - Creating new mirror configurations
 * - Managing existing mirror configurations
 * - Sync operations (trigger, cancel)
 * - Error handling
 *
 * Requires REPO_MIRROR feature to be enabled in Quay config.
 */

import {test, expect} from '../../fixtures';

test.describe(
  'Repository Mirroring',
  {tag: ['@repository', '@feature:REPO_MIRROR']},
  () => {
    test('shows state warning for non-mirror repositories and form for mirror repositories', async ({
      authenticatedPage,
      api,
    }) => {
      // Create repository in user's namespace (starts in NORMAL state)
      const repo = await api.repository(undefined, 'mirrortab');

      // Visit mirroring tab - should show state warning for NORMAL repo
      await authenticatedPage.goto(
        `/repository/${repo.fullName}?tab=mirroring`,
      );
      await expect(
        authenticatedPage.getByText("This repository's state is NORMAL"),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText(
          'Use the Settings tab and change it to Mirror',
        ),
      ).toBeVisible();

      // Change to MIRROR state via API
      await api.setMirrorState(repo.namespace, repo.name);

      // Refresh and verify form is now available
      await authenticatedPage.reload();
      await expect(authenticatedPage.getByTestId('mirror-form')).toBeVisible();
      await expect(
        authenticatedPage.getByRole('heading', {name: 'External Repository'}),
      ).toBeVisible();
    });

    test('creates new mirror configuration with form validation', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: create organization, repository, robot account
      const org = await api.organization('mirrororg');
      const repo = await api.repository(org.name, 'mirrorrepo');
      const robot = await api.robot(org.name, 'mirrorbot');
      await api.setMirrorState(org.name, repo.name);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=mirroring`,
      );

      // Wait for form to load
      await expect(authenticatedPage.getByTestId('mirror-form')).toBeVisible();

      // Verify initial form state - submit button should be disabled
      await expect(
        authenticatedPage.getByTestId('submit-button'),
      ).toBeDisabled();

      // Verify empty form fields
      await expect(
        authenticatedPage.getByTestId('registry-location-input'),
      ).toHaveValue('');
      await expect(authenticatedPage.getByTestId('tags-input')).toHaveValue('');

      // Fill in required fields one by one, verifying button stays disabled
      await authenticatedPage
        .getByTestId('registry-location-input')
        .fill('quay.io/library/alpine');
      await expect(
        authenticatedPage.getByTestId('submit-button'),
      ).toBeDisabled();

      await authenticatedPage.getByTestId('tags-input').fill('latest, 3.18');
      await expect(
        authenticatedPage.getByTestId('submit-button'),
      ).toBeDisabled();

      await authenticatedPage.getByTestId('sync-interval-input').fill('60');
      await expect(
        authenticatedPage.getByTestId('submit-button'),
      ).toBeDisabled();

      // Select robot user from dropdown
      await authenticatedPage.locator('#robot-user-select').click();
      await authenticatedPage.getByText(robot.fullName).click();

      // Now submit button should be enabled
      await expect(
        authenticatedPage.getByTestId('submit-button'),
      ).toBeEnabled();

      // Verify button text for new config
      await expect(
        authenticatedPage.getByTestId('submit-button'),
      ).toContainText('Enable Mirror');

      // Submit the form
      await authenticatedPage.getByTestId('submit-button').click();

      // Verify success message
      await expect(
        authenticatedPage.getByText('Mirror configuration saved successfully'),
      ).toBeVisible();

      // Verify mirror config exists via API
      const mirrorConfig = await api.raw.getMirrorConfig(org.name, repo.name);
      expect(mirrorConfig).not.toBeNull();
      expect(mirrorConfig?.external_reference).toBe('quay.io/library/alpine');

      // Reload page to verify form shows update mode with existing config
      await authenticatedPage.reload();
      await expect(
        authenticatedPage.getByTestId('submit-button'),
      ).toContainText('Update Mirror');
    });

    test('loads and manages existing mirror configuration', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: create org, repo, robot, set MIRROR state, create mirror config via API
      const org = await api.organization('existmirror');
      const repo = await api.repository(org.name, 'existrepo');
      const robot = await api.robot(org.name, 'existbot');
      await api.setMirrorState(org.name, repo.name);

      // Create mirror config via API
      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);
      await api.raw.createMirrorConfig(org.name, repo.name, {
        external_reference: 'quay.io/library/nginx',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
        root_rule: {
          rule_kind: 'tag_glob_csv',
          rule_value: ['latest', 'stable'],
        },
        robot_username: robot.fullName,
        skopeo_timeout_interval: 300,
        is_enabled: true,
      });

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=mirroring`,
      );

      // Wait for form to load with existing data
      await expect(authenticatedPage.getByTestId('mirror-form')).toBeVisible();

      // Verify form is populated with existing data
      await expect(
        authenticatedPage.getByTestId('registry-location-input'),
      ).toHaveValue('quay.io/library/nginx');
      await expect(authenticatedPage.getByTestId('tags-input')).toHaveValue(
        'latest, stable',
      );

      // Verify button says "Update Mirror" for existing config
      await expect(
        authenticatedPage.getByTestId('submit-button'),
      ).toContainText('Update Mirror');

      // Verify enabled checkbox is checked
      await expect(
        authenticatedPage.getByTestId('mirror-enabled-checkbox'),
      ).toBeChecked();

      // Verify status section exists
      await expect(
        authenticatedPage.getByRole('heading', {name: 'Status'}),
      ).toBeVisible();
      await expect(authenticatedPage.getByText('State')).toBeVisible();

      // Update the external reference
      await authenticatedPage
        .getByTestId('registry-location-input')
        .fill('quay.io/library/busybox');

      // Submit update
      await authenticatedPage.getByTestId('submit-button').click();

      // Verify success message
      await expect(
        authenticatedPage.getByText('Mirror configuration saved successfully'),
      ).toBeVisible();

      // Verify update via API
      const updatedConfig = await api.raw.getMirrorConfig(org.name, repo.name);
      expect(updatedConfig?.external_reference).toBe('quay.io/library/busybox');
    });

    test('triggers sync-now operation', async ({authenticatedPage, api}) => {
      // Setup: create mirror configuration via API
      const org = await api.organization('syncorg');
      const repo = await api.repository(org.name, 'syncrepo');
      const robot = await api.robot(org.name, 'syncbot');
      await api.setMirrorState(org.name, repo.name);

      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 60);
      await api.raw.createMirrorConfig(org.name, repo.name, {
        external_reference: 'quay.io/library/alpine',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
        root_rule: {
          rule_kind: 'tag_glob_csv',
          rule_value: ['latest'],
        },
        robot_username: robot.fullName,
        skopeo_timeout_interval: 300,
        is_enabled: true,
      });

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=mirroring`,
      );

      // Wait for form and sync button to be visible
      await expect(authenticatedPage.getByTestId('mirror-form')).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('sync-now-button'),
      ).toBeVisible();

      // Click sync-now button
      await authenticatedPage.getByTestId('sync-now-button').click();

      // Verify success message
      await expect(
        authenticatedPage.getByText('Sync scheduled successfully'),
      ).toBeVisible();
    });

    test('displays error on mirror configuration failure', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: create org, repo, robot, set MIRROR state
      const org = await api.organization('errororg');
      const repo = await api.repository(org.name, 'errorrepo');
      const robot = await api.robot(org.name, 'errorbot');
      await api.setMirrorState(org.name, repo.name);

      // Mock error response for POST to mirror endpoint
      // This is the ONLY acceptable mock per migration guide - error scenarios
      await authenticatedPage.route(
        `**/api/v1/repository/${org.name}/${repo.name}/mirror`,
        async (route) => {
          if (route.request().method() === 'POST') {
            await route.fulfill({
              status: 400,
              contentType: 'application/json',
              body: JSON.stringify({message: 'Invalid external reference'}),
            });
          } else {
            await route.continue();
          }
        },
      );

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=mirroring`,
      );

      // Wait for form to load
      await expect(authenticatedPage.getByTestId('mirror-form')).toBeVisible();

      // Fill in required fields
      await authenticatedPage
        .getByTestId('registry-location-input')
        .fill('invalid-registry-format');
      await authenticatedPage.getByTestId('tags-input').fill('latest');
      await authenticatedPage.getByTestId('sync-interval-input').fill('60');

      // Select robot
      await authenticatedPage.locator('#robot-user-select').click();
      await authenticatedPage.getByText(robot.fullName).click();

      // Submit form
      await authenticatedPage.getByTestId('submit-button').click();

      // Verify error message is displayed
      await expect(
        authenticatedPage.getByText('Error saving mirror configuration'),
      ).toBeVisible();
    });

    test('shows repository state setting in Settings tab', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository(undefined, 'statetest');
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=settings`);
      await expect(
        authenticatedPage.getByText('Repository state'),
      ).toBeVisible();
    });

    test('completes a real sync using authfile credentials', async ({api}) => {
      // This test waits up to 2 minutes for a real skopeo sync to complete.
      test.setTimeout(180_000);
      // Validates the authfile credential path end-to-end: if skopeomirror.py
      // writes a malformed authfile or passes credentials on the CLI instead,
      // the sync will fail or produce an error status here.
      const org = await api.organization('syncauthfileorg');
      const repo = await api.repository(org.name, 'syncauthfilerepo');
      const robot = await api.robot(org.name, 'syncauthfilebot');
      await api.setMirrorState(org.name, repo.name);

      // Mirror a small, stable public image so the sync completes quickly.
      // Push sync_start_date into the future so the scheduler won't fire
      // independently; triggerMirrorSync() is the only driver.
      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);
      await api.raw.createMirrorConfig(org.name, repo.name, {
        external_reference: 'quay.io/quay/busybox',
        sync_interval: 86400,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
        root_rule: {rule_kind: 'tag_glob_csv', rule_value: ['latest']},
        robot_username: robot.fullName,
        skopeo_timeout_interval: 300,
        is_enabled: true,
        verify_tls: true,
      });

      await api.raw.triggerMirrorSync(org.name, repo.name);

      // Poll until the mirror worker finishes. Throw on FAIL so the test
      // surfaces a clear message rather than timing out.
      await expect
        .poll(
          async () => {
            const cfg = await api.raw.getMirrorConfig(org.name, repo.name);
            const status = cfg?.sync_status ?? 'UNKNOWN';
            if (status === 'FAIL') {
              throw new Error(`Mirror sync failed with status: ${status}`);
            }
            return status;
          },
          {
            timeout: 120_000,
            intervals: [5_000, 10_000, 15_000],
            message:
              'Mirror sync did not complete successfully within 2 minutes',
          },
        )
        .toBe('SUCCESS');

      // Confirm the synced tag landed in the repository.
      const tags = await api.raw.getTags(org.name, repo.name);
      expect(tags.tags.some((t) => t.name === 'latest')).toBe(true);
    });
  },
);

/**
 * Ambient process-proxy SSRF fallback for repository mirrors.
 *
 * Requires a Quay deployment where the Quay process already has HTTP_PROXY/
 * HTTPS_PROXY (or ALL_PROXY) and SSRF_ALLOWED_HOSTS includes the upstream
 * hostname. Mirror UI/API proxy fields stay empty so validation must fall
 * back to process env (resolve_proxy_config_for_ssrf).
 *
 * Run with:
 *   PLAYWRIGHT_PROXY_SSRF_E2E=1 \
 *   PLAYWRIGHT_REPO_MIRROR_EXTERNAL_REFERENCE=<allowlisted-host/ns/repo> \
 *   npx playwright test web/playwright/e2e/repository/mirroring.spec.ts \
 *     --grep ambient
 */
const repoMirrorAmbientProxySsrfE2E =
  process.env.PLAYWRIGHT_PROXY_SSRF_E2E === '1';

test.describe(
  'Repository mirror ambient env proxy SSRF deployment',
  {tag: ['@repository', '@feature:REPO_MIRROR', '@PROJQUAY-12833']},
  () => {
    test.skip(
      !repoMirrorAmbientProxySsrfE2E,
      'requires Quay process proxy + allowlist (PLAYWRIGHT_PROXY_SSRF_E2E=1)',
    );

    test('creates mirror config with empty proxy when Quay has ambient proxy', async ({
      api,
    }) => {
      const externalReference =
        process.env.PLAYWRIGHT_REPO_MIRROR_EXTERNAL_REFERENCE;
      test.skip(
        !externalReference,
        'PLAYWRIGHT_REPO_MIRROR_EXTERNAL_REFERENCE not set',
      );

      const org = await api.organization('mirrorenvproxy');
      const repo = await api.repository(org.name, 'envproxyrepo');
      const robot = await api.robot(org.name, 'envproxybot');
      await api.setMirrorState(org.name, repo.name);

      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 60);
      await api.raw.createMirrorConfig(org.name, repo.name, {
        external_reference: externalReference,
        sync_interval: 86400,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
        root_rule: {
          rule_kind: 'tag_glob_csv',
          rule_value: ['latest'],
        },
        robot_username: robot.fullName,
        is_enabled: false,
        external_registry_config: {
          verify_tls: true,
          unsigned_images: false,
          proxy: {
            http_proxy: null,
            https_proxy: null,
            no_proxy: null,
          },
        },
      });

      const mirrorConfig = await api.raw.getMirrorConfig(org.name, repo.name);
      expect(mirrorConfig).not.toBeNull();
      expect(mirrorConfig?.external_reference).toBe(externalReference);
      expect(
        mirrorConfig?.external_registry_config?.proxy?.http_proxy,
      ).toBeFalsy();
      expect(
        mirrorConfig?.external_registry_config?.proxy?.https_proxy,
      ).toBeFalsy();
    });

    test('rejects non-allowlisted unresolved upstream with empty proxy', async ({
      api,
    }) => {
      const externalReference =
        process.env.PLAYWRIGHT_REPO_MIRROR_NON_ALLOWLISTED_EXTERNAL_REFERENCE ??
        'non-allowlisted-isolated.example.com/team/repo';

      const org = await api.organization('mirrorenvfail');
      const repo = await api.repository(org.name, 'envfailrepo');
      const robot = await api.robot(org.name, 'envfailbot');
      await api.setMirrorState(org.name, repo.name);

      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 60);
      await expect(
        api.raw.createMirrorConfig(org.name, repo.name, {
          external_reference: externalReference,
          sync_interval: 86400,
          sync_start_date: syncStartDate
            .toISOString()
            .replace(/\.\d{3}Z$/, 'Z'),
          root_rule: {
            rule_kind: 'tag_glob_csv',
            rule_value: ['latest'],
          },
          robot_username: robot.fullName,
          is_enabled: false,
          external_registry_config: {
            verify_tls: true,
            proxy: {
              http_proxy: null,
              https_proxy: null,
              no_proxy: null,
            },
          },
        }),
      ).rejects.toThrow(/400|not allowed/i);

      const mirrorConfig = await api.raw.getMirrorConfig(org.name, repo.name);
      expect(mirrorConfig).toBeNull();
    });
  },
);
