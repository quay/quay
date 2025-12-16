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

import {test, expect, uniqueName, skipUnlessFeature} from '../../fixtures';
import {ApiClient} from '../../utils/api';
import {TEST_USERS} from '../../global-setup';

test.describe(
  'Repository Mirroring',
  {tag: ['@repository', '@feature:REPO_MIRROR']},
  () => {
    test('shows state warning for non-mirror repositories and form for mirror repositories', async ({
      authenticatedPage,
      authenticatedRequest,
      quayConfig,
    }) => {
      test.skip(...skipUnlessFeature(quayConfig, 'REPO_MIRROR'));

      const api = new ApiClient(authenticatedRequest);
      const repoName = uniqueName('mirrortab');
      const namespace = TEST_USERS.user.username;

      // Create repository (starts in NORMAL state)
      await api.createRepository(namespace, repoName);

      try {
        // Visit mirroring tab - should show state warning for NORMAL repo
        await authenticatedPage.goto(
          `/repository/${namespace}/${repoName}?tab=mirroring`,
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
        await api.changeRepositoryState(namespace, repoName, 'MIRROR');

        // Refresh and verify form is now available
        await authenticatedPage.reload();
        await expect(
          authenticatedPage.getByTestId('mirror-form'),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByRole('heading', {name: 'External Repository'}),
        ).toBeVisible();
      } finally {
        await api.deleteRepository(namespace, repoName);
      }
    });

    test('creates new mirror configuration with form validation', async ({
      authenticatedPage,
      authenticatedRequest,
      quayConfig,
    }) => {
      test.skip(...skipUnlessFeature(quayConfig, 'REPO_MIRROR'));

      const api = new ApiClient(authenticatedRequest);
      const orgName = uniqueName('mirrororg');
      const repoName = uniqueName('mirrorrepo');
      const robotShortname = uniqueName('mirrorbot');

      // Setup: create organization, repository, robot account
      await api.createOrganization(orgName);
      await api.createRepository(orgName, repoName);
      await api.createRobot(orgName, robotShortname);
      await api.changeRepositoryState(orgName, repoName, 'MIRROR');

      try {
        await authenticatedPage.goto(
          `/repository/${orgName}/${repoName}?tab=mirroring`,
        );

        // Wait for form to load
        await expect(
          authenticatedPage.getByTestId('mirror-form'),
        ).toBeVisible();

        // Verify initial form state - submit button should be disabled
        await expect(
          authenticatedPage.getByTestId('submit-button'),
        ).toBeDisabled();

        // Verify empty form fields
        await expect(
          authenticatedPage.getByTestId('registry-location-input'),
        ).toHaveValue('');
        await expect(authenticatedPage.getByTestId('tags-input')).toHaveValue(
          '',
        );

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
        await authenticatedPage
          .getByText(`${orgName}+${robotShortname}`)
          .click();

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
          authenticatedPage.getByText(
            'Mirror configuration saved successfully',
          ),
        ).toBeVisible();

        // Verify mirror config exists via API
        const mirrorConfig = await api.getMirrorConfig(orgName, repoName);
        expect(mirrorConfig).not.toBeNull();
        expect(mirrorConfig?.external_reference).toBe('quay.io/library/alpine');

        // Reload page to verify form shows update mode with existing config
        await authenticatedPage.reload();
        await expect(
          authenticatedPage.getByTestId('submit-button'),
        ).toContainText('Update Mirror');
      } finally {
        // Cleanup in order: repo first (removes mirror config), then robot, then org
        try {
          await api.deleteRepository(orgName, repoName);
        } catch {
          // Already deleted or doesn't exist
        }
        try {
          await api.deleteRobot(orgName, robotShortname);
        } catch {
          // Already deleted or doesn't exist
        }
        try {
          await api.deleteOrganization(orgName);
        } catch {
          // Already deleted or doesn't exist
        }
      }
    });

    test('loads and manages existing mirror configuration', async ({
      authenticatedPage,
      authenticatedRequest,
      quayConfig,
    }) => {
      test.skip(...skipUnlessFeature(quayConfig, 'REPO_MIRROR'));

      const api = new ApiClient(authenticatedRequest);
      const orgName = uniqueName('existmirror');
      const repoName = uniqueName('existrepo');
      const robotShortname = uniqueName('existbot');
      const robotUsername = `${orgName}+${robotShortname}`;

      // Setup: create org, repo, robot, set MIRROR state, create mirror config via API
      await api.createOrganization(orgName);
      await api.createRepository(orgName, repoName);
      await api.createRobot(orgName, robotShortname);
      await api.changeRepositoryState(orgName, repoName, 'MIRROR');

      // Create mirror config via API
      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);
      await api.createMirrorConfig(orgName, repoName, {
        external_reference: 'quay.io/library/nginx',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
        root_rule: {
          rule_kind: 'tag_glob_csv',
          rule_value: ['latest', 'stable'],
        },
        robot_username: robotUsername,
        skopeo_timeout_interval: 300,
        is_enabled: true,
      });

      try {
        await authenticatedPage.goto(
          `/repository/${orgName}/${repoName}?tab=mirroring`,
        );

        // Wait for form to load with existing data
        await expect(
          authenticatedPage.getByTestId('mirror-form'),
        ).toBeVisible();

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
          authenticatedPage.getByText(
            'Mirror configuration saved successfully',
          ),
        ).toBeVisible();

        // Verify update via API
        const updatedConfig = await api.getMirrorConfig(orgName, repoName);
        expect(updatedConfig?.external_reference).toBe(
          'quay.io/library/busybox',
        );
      } finally {
        // Cleanup in order: repo first (removes mirror config), then robot, then org
        try {
          await api.deleteRepository(orgName, repoName);
        } catch {
          // Already deleted or doesn't exist
        }
        try {
          await api.deleteRobot(orgName, robotShortname);
        } catch {
          // Already deleted or doesn't exist
        }
        try {
          await api.deleteOrganization(orgName);
        } catch {
          // Already deleted or doesn't exist
        }
      }
    });

    test('triggers sync-now operation', async ({
      authenticatedPage,
      authenticatedRequest,
      quayConfig,
    }) => {
      test.skip(...skipUnlessFeature(quayConfig, 'REPO_MIRROR'));

      const api = new ApiClient(authenticatedRequest);
      const orgName = uniqueName('syncorg');
      const repoName = uniqueName('syncrepo');
      const robotShortname = uniqueName('syncbot');
      const robotUsername = `${orgName}+${robotShortname}`;

      // Setup: create mirror configuration via API
      await api.createOrganization(orgName);
      await api.createRepository(orgName, repoName);
      await api.createRobot(orgName, robotShortname);
      await api.changeRepositoryState(orgName, repoName, 'MIRROR');

      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 60);
      await api.createMirrorConfig(orgName, repoName, {
        external_reference: 'quay.io/library/alpine',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
        root_rule: {
          rule_kind: 'tag_glob_csv',
          rule_value: ['latest'],
        },
        robot_username: robotUsername,
        skopeo_timeout_interval: 300,
        is_enabled: true,
      });

      try {
        await authenticatedPage.goto(
          `/repository/${orgName}/${repoName}?tab=mirroring`,
        );

        // Wait for form and sync button to be visible
        await expect(
          authenticatedPage.getByTestId('mirror-form'),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByTestId('sync-now-button'),
        ).toBeVisible();

        // Click sync-now button
        await authenticatedPage.getByTestId('sync-now-button').click();

        // Verify success message
        await expect(
          authenticatedPage.getByText('Sync scheduled successfully'),
        ).toBeVisible();
      } finally {
        // Cleanup in order: repo first (removes mirror config), then robot, then org
        try {
          await api.deleteRepository(orgName, repoName);
        } catch {
          // Already deleted or doesn't exist
        }
        try {
          await api.deleteRobot(orgName, robotShortname);
        } catch {
          // Already deleted or doesn't exist
        }
        try {
          await api.deleteOrganization(orgName);
        } catch {
          // Already deleted or doesn't exist
        }
      }
    });

    test('displays error on mirror configuration failure', async ({
      authenticatedPage,
      authenticatedRequest,
      quayConfig,
    }) => {
      test.skip(...skipUnlessFeature(quayConfig, 'REPO_MIRROR'));

      const api = new ApiClient(authenticatedRequest);
      const orgName = uniqueName('errororg');
      const repoName = uniqueName('errorrepo');
      const robotShortname = uniqueName('errorbot');

      // Setup: create org, repo, robot, set MIRROR state
      await api.createOrganization(orgName);
      await api.createRepository(orgName, repoName);
      await api.createRobot(orgName, robotShortname);
      await api.changeRepositoryState(orgName, repoName, 'MIRROR');

      try {
        // Mock error response for POST to mirror endpoint
        // This is the ONLY acceptable mock per migration guide - error scenarios
        await authenticatedPage.route(
          `**/api/v1/repository/${orgName}/${repoName}/mirror`,
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
          `/repository/${orgName}/${repoName}?tab=mirroring`,
        );

        // Wait for form to load
        await expect(
          authenticatedPage.getByTestId('mirror-form'),
        ).toBeVisible();

        // Fill in required fields
        await authenticatedPage
          .getByTestId('registry-location-input')
          .fill('invalid-registry-format');
        await authenticatedPage.getByTestId('tags-input').fill('latest');
        await authenticatedPage.getByTestId('sync-interval-input').fill('60');

        // Select robot
        await authenticatedPage.locator('#robot-user-select').click();
        await authenticatedPage
          .getByText(`${orgName}+${robotShortname}`)
          .click();

        // Submit form
        await authenticatedPage.getByTestId('submit-button').click();

        // Verify error message is displayed
        await expect(
          authenticatedPage.getByText('Error saving mirror configuration'),
        ).toBeVisible();
      } finally {
        // Cleanup in order: repo first (removes mirror config), then robot, then org
        try {
          await api.deleteRepository(orgName, repoName);
        } catch {
          // Already deleted or doesn't exist
        }
        try {
          await api.deleteRobot(orgName, robotShortname);
        } catch {
          // Already deleted or doesn't exist
        }
        try {
          await api.deleteOrganization(orgName);
        } catch {
          // Already deleted or doesn't exist
        }
      }
    });
  },
);
