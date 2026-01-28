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
      await expect(authenticatedPage.getByText('Status')).toBeVisible();
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

    test('displays architecture filter component with all architectures option', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: create org, repo, set MIRROR state
      const org = await api.organization('archfilterorg');
      const repo = await api.repository(org.name, 'archfilterrepo');
      await api.setMirrorState(org.name, repo.name);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=mirroring`,
      );

      // Wait for form to load
      await expect(authenticatedPage.getByTestId('mirror-form')).toBeVisible();

      // Verify architecture filter component is present
      await expect(
        authenticatedPage.getByTestId('architecture-filter-toggle'),
      ).toBeVisible();

      // Verify default text shows "All architectures"
      await expect(
        authenticatedPage.getByTestId('architecture-filter-toggle'),
      ).toContainText('All architectures');

      // Verify helper text for empty selection
      await expect(
        authenticatedPage.getByTestId('architecture-filter-helper'),
      ).toContainText('All architectures will be mirrored');
    });

    test('allows selecting multiple architectures from dropdown', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: create org, repo, set MIRROR state
      const org = await api.organization('archselectorg');
      const repo = await api.repository(org.name, 'archselectrepo');
      await api.setMirrorState(org.name, repo.name);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=mirroring`,
      );

      // Wait for form to load
      await expect(authenticatedPage.getByTestId('mirror-form')).toBeVisible();

      // Open the architecture filter dropdown
      await authenticatedPage.getByTestId('architecture-filter-toggle').click();

      // Verify all architecture options are visible
      await expect(
        authenticatedPage.getByTestId('architecture-option-amd64'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('architecture-option-arm64'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('architecture-option-ppc64le'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('architecture-option-s390x'),
      ).toBeVisible();

      // Select amd64
      await authenticatedPage.getByTestId('architecture-option-amd64').click();

      // Dropdown stays open for multi-select, select arm64
      await authenticatedPage.getByTestId('architecture-option-arm64').click();

      // Close dropdown by clicking outside
      await authenticatedPage.getByTestId('mirror-form').click();

      // Verify badge shows 2
      await expect(
        authenticatedPage.getByTestId('architecture-filter-badge'),
      ).toContainText('2');

      // Verify helper text shows selected architectures
      await expect(
        authenticatedPage.getByTestId('architecture-filter-helper'),
      ).toContainText('amd64');
      await expect(
        authenticatedPage.getByTestId('architecture-filter-helper'),
      ).toContainText('arm64');
    });

    test('saves and loads architecture filter with mirror configuration', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: create org, repo, robot, set MIRROR state
      const org = await api.organization('archsaveorg');
      const repo = await api.repository(org.name, 'archsaverepo');
      const robot = await api.robot(org.name, 'archsavebot');
      await api.setMirrorState(org.name, repo.name);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=mirroring`,
      );

      // Wait for form to load
      await expect(authenticatedPage.getByTestId('mirror-form')).toBeVisible();

      // Fill in required fields
      await authenticatedPage
        .getByTestId('registry-location-input')
        .fill('quay.io/library/alpine');
      await authenticatedPage.getByTestId('tags-input').fill('latest');
      await authenticatedPage.getByTestId('sync-interval-input').fill('60');

      // Select robot user
      await authenticatedPage.locator('#robot-user-select').click();
      await authenticatedPage.getByText(robot.fullName).click();

      // Select architecture filter: amd64 and arm64
      await authenticatedPage.getByTestId('architecture-filter-toggle').click();
      await expect(
        authenticatedPage.getByTestId('architecture-option-amd64'),
      ).toBeVisible();
      await authenticatedPage.getByTestId('architecture-option-amd64').click();
      // Dropdown stays open for multi-select
      await authenticatedPage.getByTestId('architecture-option-arm64').click();
      // Close the dropdown by clicking outside
      await authenticatedPage.getByTestId('mirror-form').click();

      // Submit the form
      await authenticatedPage.getByTestId('submit-button').click();

      // Verify success message
      await expect(
        authenticatedPage.getByText('Mirror configuration saved successfully'),
      ).toBeVisible();

      // Verify architecture filter was saved via API
      const mirrorConfig = await api.raw.getMirrorConfig(org.name, repo.name);
      expect(mirrorConfig?.architecture_filter).toContain('amd64');
      expect(mirrorConfig?.architecture_filter).toContain('arm64');
      expect(mirrorConfig?.architecture_filter?.length).toBe(2);

      // Reload page to verify filter persists
      await authenticatedPage.reload();
      await expect(authenticatedPage.getByTestId('mirror-form')).toBeVisible();

      // Verify architecture filter shows saved selection
      await expect(
        authenticatedPage.getByTestId('architecture-filter-badge'),
      ).toContainText('2');
      await expect(
        authenticatedPage.getByTestId('architecture-filter-helper'),
      ).toContainText('amd64');
      await expect(
        authenticatedPage.getByTestId('architecture-filter-helper'),
      ).toContainText('arm64');
    });

    test('clears architecture filter selection', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: create org, repo, set MIRROR state
      const org = await api.organization('archclearorg');
      const repo = await api.repository(org.name, 'archclearrepo');
      await api.setMirrorState(org.name, repo.name);

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=mirroring`,
      );

      // Wait for form to load
      await expect(authenticatedPage.getByTestId('mirror-form')).toBeVisible();

      // Open dropdown and select some architectures
      await authenticatedPage.getByTestId('architecture-filter-toggle').click();
      await expect(
        authenticatedPage.getByTestId('architecture-option-amd64'),
      ).toBeVisible();
      await authenticatedPage.getByTestId('architecture-option-amd64').click();
      // Dropdown stays open for multi-select
      await authenticatedPage.getByTestId('architecture-option-arm64').click();
      // Close the dropdown by clicking outside
      await authenticatedPage.getByTestId('mirror-form').click();

      // Verify selections were made
      await expect(
        authenticatedPage.getByTestId('architecture-filter-badge'),
      ).toContainText('2');

      // Open dropdown and click "Clear all"
      await authenticatedPage.getByTestId('architecture-filter-toggle').click();
      await authenticatedPage.getByTestId('architecture-clear-all').click();

      // Verify selection is cleared
      await expect(
        authenticatedPage.getByTestId('architecture-filter-toggle'),
      ).toContainText('All architectures');
      await expect(
        authenticatedPage.getByTestId('architecture-filter-helper'),
      ).toContainText('All architectures will be mirrored');
    });

    test('loads existing architecture filter from saved mirror configuration', async ({
      authenticatedPage,
      api,
    }) => {
      // Setup: create org, repo, robot, set MIRROR state, create mirror config with architecture filter
      const org = await api.organization('archloadorg');
      const repo = await api.repository(org.name, 'archloadrepo');
      const robot = await api.robot(org.name, 'archloadbot');
      await api.setMirrorState(org.name, repo.name);

      // Create mirror config via API with architecture filter
      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);
      await api.raw.createMirrorConfig(org.name, repo.name, {
        external_reference: 'quay.io/library/nginx',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
        root_rule: {
          rule_kind: 'tag_glob_csv',
          rule_value: ['latest'],
        },
        robot_username: robot.fullName,
        skopeo_timeout_interval: 300,
        is_enabled: true,
        architecture_filter: ['ppc64le', 's390x'],
      });

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=mirroring`,
      );

      // Wait for form to load
      await expect(authenticatedPage.getByTestId('mirror-form')).toBeVisible();

      // Verify architecture filter shows the saved selection
      await expect(
        authenticatedPage.getByTestId('architecture-filter-badge'),
      ).toContainText('2');
      await expect(
        authenticatedPage.getByTestId('architecture-filter-helper'),
      ).toContainText('ppc64le');
      await expect(
        authenticatedPage.getByTestId('architecture-filter-helper'),
      ).toContainText('s390x');
    });
  },
);
