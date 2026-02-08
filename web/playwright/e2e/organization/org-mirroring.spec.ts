/**
 * Organization Mirroring E2E Tests
 *
 * Tests for organization-level mirroring functionality including:
 * - Feature flag behavior and tab visibility
 * - Creating new mirror configurations
 * - Managing existing mirror configurations
 * - Sync operations (trigger, cancel)
 * - Verify connection
 * - Deleting configurations
 * - Discovered repositories table
 * - Error handling
 *
 * Requires ORG_MIRROR feature to be enabled in Quay config.
 */

import {test, expect} from '../../fixtures';
import {Page} from '@playwright/test';

async function fillRequiredFields(
  page: Page,
  robotFullName: string,
  options: {
    registryUrl?: string;
    namespace?: string;
    syncInterval?: string;
  } = {},
) {
  const {
    registryUrl = 'https://quay.io',
    namespace = 'projectquay',
    syncInterval = '60',
  } = options;

  await page.getByTestId('registry-url-input').fill(registryUrl);
  await page.getByTestId('namespace-input').fill(namespace);
  await page.getByTestId('sync-interval-input').fill(syncInterval);

  const futureDate = new Date();
  futureDate.setMinutes(futureDate.getMinutes() + 5);
  await page
    .locator('#sync_start_date')
    .fill(futureDate.toISOString().slice(0, 16));

  await page.locator('#robot-user-select').click();
  await page.getByRole('option', {name: robotFullName}).click();
}

test.describe(
  'Organization Mirroring',
  {tag: ['@organization', '@feature:ORG_MIRROR']},
  () => {
    test('shows NORMAL state message when no config exists', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrnorm');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Mirroring`);

      await expect(
        authenticatedPage.getByText("This organization's state is"),
      ).toBeVisible();
      await expect(authenticatedPage.getByText('NORMAL')).toBeVisible();
      await expect(authenticatedPage.getByText('Settings tab')).toBeVisible();
    });

    test('shows mirroring tab only for org admins when feature is enabled', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrvis');

      await authenticatedPage.goto(`/organization/${org.name}`);

      // Mirroring tab should be visible for org admin
      await expect(
        authenticatedPage.getByRole('tab', {name: 'Mirroring'}),
      ).toBeVisible();
    });

    test('settings tab shows organization state with mirror option', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrsett');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Click on "Organization state" settings tab
      await authenticatedPage.getByText('Organization state').click();

      // Verify Normal and Mirror radio buttons are visible
      await expect(
        authenticatedPage.getByRole('radio', {name: 'Normal'}),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('radio', {name: 'Mirror'}),
      ).toBeVisible();
    });

    test('navigates from settings mirror state to mirroring tab', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrsnav');

      await authenticatedPage.goto(`/organization/${org.name}?tab=Settings`);

      // Click on "Organization state" settings tab
      await authenticatedPage.getByText('Organization state').click();

      // Select Mirror radio
      await authenticatedPage.getByRole('radio', {name: 'Mirror'}).click();

      // Verify info alert appears
      await expect(
        authenticatedPage.getByText(
          'Selecting Mirror will take you to the Mirroring tab',
        ),
      ).toBeVisible();

      // Submit
      await authenticatedPage.getByRole('button', {name: 'Submit'}).click();

      // Verify navigated to Mirroring tab with setup mode
      await expect(authenticatedPage).toHaveURL(/tab=Mirroring/);
      await expect(authenticatedPage).toHaveURL(/setup=true/);
    });

    test('creates new mirror configuration with form validation', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrcrt');
      const robot = await api.robot(org.name, 'mirrorbot');

      // Navigate to mirroring tab in setup mode
      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Mirroring&setup=true`,
      );

      // Wait for form to load
      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Verify submit button is disabled initially (required fields empty)
      await expect(
        authenticatedPage.getByTestId('submit-button'),
      ).toBeDisabled();

      // Verify button says "Enable Organization Mirror" for new config
      await expect(
        authenticatedPage.getByTestId('submit-button'),
      ).toContainText('Enable Organization Mirror');

      // Fill in required fields
      await fillRequiredFields(authenticatedPage, robot.fullName);

      // Now submit button should be enabled
      await expect(
        authenticatedPage.getByTestId('submit-button'),
      ).toBeEnabled();

      // Submit the form
      await authenticatedPage.getByTestId('submit-button').click();

      // Verify success message
      await expect(
        authenticatedPage
          .getByText('Organization mirror configuration saved successfully')
          .first(),
      ).toBeVisible();

      // Verify config exists via API
      const config = await api.raw.getOrgMirrorConfig(org.name);
      expect(config).not.toBeNull();
      expect(config?.external_registry_url).toBe('https://quay.io');
      expect(config?.external_namespace).toBe('projectquay');
    });

    test('loads and manages existing mirror configuration', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrexst');
      const robot = await api.robot(org.name, 'existbot');

      // Create config via API
      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);
      await api.raw.createOrgMirrorConfig(org.name, {
        external_registry_type: 'quay',
        external_registry_url: 'https://quay.io',
        external_namespace: 'projectquay',
        robot_username: robot.fullName,
        visibility: 'private',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
        repository_filters: ['clair*', 'quay'],
      });

      await authenticatedPage.goto(`/organization/${org.name}?tab=Mirroring`);

      // Wait for form to load with existing data
      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Verify form is populated with existing data
      await expect(
        authenticatedPage.getByTestId('registry-url-input'),
      ).toHaveValue('https://quay.io');
      await expect(
        authenticatedPage.getByTestId('namespace-input'),
      ).toHaveValue('projectquay');

      // Verify button says "Update Organization Mirror" for existing config
      await expect(
        authenticatedPage.getByTestId('submit-button'),
      ).toContainText('Update Organization Mirror');

      // Verify enabled checkbox is visible and checked
      await expect(
        authenticatedPage.getByTestId('org-mirror-enabled-checkbox'),
      ).toBeChecked();

      // Verify status section exists
      const statusDisplay = authenticatedPage.getByTestId(
        'org-mirror-status-display',
      );
      await expect(statusDisplay).toBeVisible();
      await expect(statusDisplay.getByText('State')).toBeVisible();

      // Update the namespace
      await authenticatedPage
        .getByTestId('namespace-input')
        .fill('newnamespace');

      // Submit update
      await authenticatedPage.getByTestId('submit-button').click();

      // Verify success message
      await expect(
        authenticatedPage
          .getByText('Organization mirror configuration saved successfully')
          .first(),
      ).toBeVisible();

      // Verify update via API
      const updatedConfig = await api.raw.getOrgMirrorConfig(org.name);
      expect(updatedConfig?.external_namespace).toBe('newnamespace');
    });

    test('triggers sync-now operation', async ({authenticatedPage, api}) => {
      const org = await api.organization('orgmirrsync');
      const robot = await api.robot(org.name, 'syncbot');

      // Create config via API with future start date
      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 60);
      await api.raw.createOrgMirrorConfig(org.name, {
        external_registry_type: 'quay',
        external_registry_url: 'https://quay.io',
        external_namespace: 'projectquay',
        robot_username: robot.fullName,
        visibility: 'private',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
      });

      await authenticatedPage.goto(`/organization/${org.name}?tab=Mirroring`);

      // Wait for form and sync button to be visible
      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('sync-now-button'),
      ).toBeVisible();

      // Click sync-now button
      await authenticatedPage.getByTestId('sync-now-button').click();

      // Verify success message
      await expect(
        authenticatedPage
          .getByText('Organization sync scheduled successfully')
          .first(),
      ).toBeVisible();
    });

    test('verifies connection to source registry', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrverf');
      const robot = await api.robot(org.name, 'verfbot');

      // Create config via API
      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);
      await api.raw.createOrgMirrorConfig(org.name, {
        external_registry_type: 'quay',
        external_registry_url: 'https://quay.io',
        external_namespace: 'projectquay',
        robot_username: robot.fullName,
        visibility: 'private',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
      });

      await authenticatedPage.goto(`/organization/${org.name}?tab=Mirroring`);

      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Click verify connection button
      await expect(
        authenticatedPage.getByTestId('verify-connection-button'),
      ).toBeVisible();
      await authenticatedPage.getByTestId('verify-connection-button').click();

      // Verify a result message appears (success or failure depending on connectivity)
      await expect(
        authenticatedPage
          .getByText(
            /Connection verified|Connection verification failed|Error verifying/,
          )
          .first(),
      ).toBeVisible({timeout: 15000});
    });

    test('deletes mirror configuration with confirmation', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrdel');
      const robot = await api.robot(org.name, 'delbot');

      // Create config via API
      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);
      await api.raw.createOrgMirrorConfig(org.name, {
        external_registry_type: 'harbor',
        external_registry_url: 'https://harbor.example.com',
        external_namespace: 'library',
        robot_username: robot.fullName,
        visibility: 'private',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
      });

      await authenticatedPage.goto(`/organization/${org.name}?tab=Mirroring`);

      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Click delete button
      await authenticatedPage.getByTestId('delete-mirror-button').click();

      // Verify confirmation modal appears
      await expect(
        authenticatedPage
          .getByText(
            'Are you sure you want to delete the organization mirror configuration?',
          )
          .first(),
      ).toBeVisible();

      // Click confirm
      await authenticatedPage.getByTestId('confirm-delete-button').click();

      // Verify success message
      await expect(
        authenticatedPage
          .getByText('Organization mirror configuration deleted successfully')
          .first(),
      ).toBeVisible();

      // Verify config is gone via API
      const config = await api.raw.getOrgMirrorConfig(org.name);
      expect(config).toBeNull();
    });

    test('displays error on mirror configuration failure', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrerr');
      const robot = await api.robot(org.name, 'errbot');

      // Mock error response for POST to org mirror endpoint
      await authenticatedPage.route(
        `**/api/v1/organization/${org.name}/mirror`,
        async (route) => {
          if (route.request().method() === 'POST') {
            await route.fulfill({
              status: 400,
              contentType: 'application/json',
              body: JSON.stringify({
                message: 'Invalid configuration',
              }),
            });
          } else {
            await route.continue();
          }
        },
      );

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Mirroring&setup=true`,
      );

      // Wait for form to load
      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Fill in required fields
      await fillRequiredFields(authenticatedPage, robot.fullName, {
        namespace: 'testns',
      });

      // Submit form
      await authenticatedPage.getByTestId('submit-button').click();

      // Verify error message is displayed
      await expect(
        authenticatedPage
          .getByText('Error saving organization mirror configuration')
          .first(),
      ).toBeVisible();
    });

    test('shows discovered repositories table when config exists', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrrepo');
      const robot = await api.robot(org.name, 'repobot');

      // Create config via API
      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);
      await api.raw.createOrgMirrorConfig(org.name, {
        external_registry_type: 'quay',
        external_registry_url: 'https://quay.io',
        external_namespace: 'projectquay',
        robot_username: robot.fullName,
        visibility: 'private',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
      });

      await authenticatedPage.goto(`/organization/${org.name}?tab=Mirroring`);

      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Verify discovered repositories section exists
      await expect(
        authenticatedPage.getByText('Discovered Repositories'),
      ).toBeVisible();
    });

    test('toggles enabled checkbox and updates config', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrtgl');
      const robot = await api.robot(org.name, 'tglbot');

      // Create config via API (enabled by default)
      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);
      await api.raw.createOrgMirrorConfig(org.name, {
        external_registry_type: 'quay',
        external_registry_url: 'https://quay.io',
        external_namespace: 'projectquay',
        robot_username: robot.fullName,
        visibility: 'private',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
        is_enabled: true,
      });

      await authenticatedPage.goto(`/organization/${org.name}?tab=Mirroring`);

      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Verify checkbox is checked
      await expect(
        authenticatedPage.getByTestId('org-mirror-enabled-checkbox'),
      ).toBeChecked();

      // Uncheck it
      await authenticatedPage
        .getByTestId('org-mirror-enabled-checkbox')
        .click();

      // Verify success message for disable
      await expect(
        authenticatedPage
          .getByText('Organization mirror disabled successfully')
          .first(),
      ).toBeVisible();

      // Verify via API
      const config = await api.raw.getOrgMirrorConfig(org.name);
      expect(config?.is_enabled).toBe(false);
    });

    test('cancel sync button is disabled when not syncing', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrcanc');
      const robot = await api.robot(org.name, 'cancbot');

      // Create config in NEVER_RUN state
      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 60);
      await api.raw.createOrgMirrorConfig(org.name, {
        external_registry_type: 'quay',
        external_registry_url: 'https://quay.io',
        external_namespace: 'projectquay',
        robot_username: robot.fullName,
        visibility: 'private',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
      });

      await authenticatedPage.goto(`/organization/${org.name}?tab=Mirroring`);

      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Cancel sync button should be disabled when not syncing
      await expect(
        authenticatedPage.getByTestId('cancel-sync-button'),
      ).toBeDisabled();
    });

    test('repository filters are preserved on save', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrfilt');
      const robot = await api.robot(org.name, 'filtbot');

      // Navigate in setup mode
      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Mirroring&setup=true`,
      );

      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Fill required fields
      await fillRequiredFields(authenticatedPage, robot.fullName);

      // Add repository filters
      await authenticatedPage
        .getByTestId('repository-filters-input')
        .fill('nginx*, redis, app-*');

      // Submit
      await authenticatedPage.getByTestId('submit-button').click();

      // Verify success
      await expect(
        authenticatedPage
          .getByText('Organization mirror configuration saved successfully')
          .first(),
      ).toBeVisible();

      // Verify filters saved via API
      const config = await api.raw.getOrgMirrorConfig(org.name);
      expect(config?.repository_filters).toContain('nginx*');
      expect(config?.repository_filters).toContain('redis');
      expect(config?.repository_filters).toContain('app-*');
    });

    test('creates config with Harbor registry type', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrharb');
      const robot = await api.robot(org.name, 'harbbot');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Mirroring&setup=true`,
      );

      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Select Harbor registry type
      await authenticatedPage.getByTestId('registry-type-toggle').click();
      await authenticatedPage.getByRole('option', {name: 'Harbor'}).click();

      // Fill in required fields with Harbor URL
      await fillRequiredFields(authenticatedPage, robot.fullName, {
        registryUrl: 'https://harbor.example.com',
        namespace: 'library',
      });

      // Submit
      await authenticatedPage.getByTestId('submit-button').click();

      await expect(
        authenticatedPage
          .getByText('Organization mirror configuration saved successfully')
          .first(),
      ).toBeVisible();

      // Verify Harbor type saved via API
      const config = await api.raw.getOrgMirrorConfig(org.name);
      expect(config?.external_registry_type).toBe('harbor');
      expect(config?.external_registry_url).toBe('https://harbor.example.com');
    });

    test('changes visibility from private to public and saves', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrpub');
      const robot = await api.robot(org.name, 'pubbot');

      // Create config with private visibility
      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);
      await api.raw.createOrgMirrorConfig(org.name, {
        external_registry_type: 'quay',
        external_registry_url: 'https://quay.io',
        external_namespace: 'projectquay',
        robot_username: robot.fullName,
        visibility: 'private',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
      });

      await authenticatedPage.goto(`/organization/${org.name}?tab=Mirroring`);

      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Verify private is initially selected
      await expect(
        authenticatedPage.getByTestId('visibility-private'),
      ).toBeChecked();

      // Switch to public
      await authenticatedPage.getByTestId('visibility-public').click();

      // Submit
      await authenticatedPage.getByTestId('submit-button').click();

      await expect(
        authenticatedPage
          .getByText('Organization mirror configuration saved successfully')
          .first(),
      ).toBeVisible();

      // Verify via API
      const config = await api.raw.getOrgMirrorConfig(org.name);
      expect(config?.visibility).toBe('public');
    });

    test('saves advanced settings (TLS and proxy)', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirradv');
      const robot = await api.robot(org.name, 'advbot');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Mirroring&setup=true`,
      );

      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Fill required fields
      await fillRequiredFields(authenticatedPage, robot.fullName, {
        namespace: 'testns',
      });

      // Uncheck TLS verification
      await authenticatedPage.getByTestId('verify-tls-checkbox').click();

      // Fill in proxy settings
      await authenticatedPage
        .getByTestId('http-proxy-input')
        .fill('http://proxy.example.com:8080');
      await authenticatedPage
        .getByTestId('https-proxy-input')
        .fill('https://proxy.example.com:8443');
      await authenticatedPage
        .getByTestId('no-proxy-input')
        .fill('localhost,127.0.0.1');

      // Submit
      await authenticatedPage.getByTestId('submit-button').click();

      await expect(
        authenticatedPage
          .getByText('Organization mirror configuration saved successfully')
          .first(),
      ).toBeVisible();

      // Verify via API
      const config = await api.raw.getOrgMirrorConfig(org.name);
      expect(config?.external_registry_config?.verify_tls).toBe(false);
      expect(config?.external_registry_config?.proxy?.http_proxy).toBe(
        'http://proxy.example.com:8080',
      );
      expect(config?.external_registry_config?.proxy?.https_proxy).toBe(
        'https://proxy.example.com:8443',
      );
      expect(config?.external_registry_config?.proxy?.no_proxy).toBe(
        'localhost,127.0.0.1',
      );
    });

    test('saves credentials (username and password)', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrcred');
      const robot = await api.robot(org.name, 'credbot');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Mirroring&setup=true`,
      );

      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Fill required fields
      await fillRequiredFields(authenticatedPage, robot.fullName, {
        namespace: 'testns',
      });

      // Fill in credentials
      await authenticatedPage.getByTestId('username-input').fill('testuser');
      await authenticatedPage.getByTestId('password-input').fill('testpass');

      // Submit
      await authenticatedPage.getByTestId('submit-button').click();

      await expect(
        authenticatedPage
          .getByText('Organization mirror configuration saved successfully')
          .first(),
      ).toBeVisible();

      // Verify username saved via API (password is not returned)
      const config = await api.raw.getOrgMirrorConfig(org.name);
      expect(config?.external_registry_username).toBe('testuser');
    });

    test('validates skopeo timeout range', async ({authenticatedPage, api}) => {
      const org = await api.organization('orgmirrskop');
      const robot = await api.robot(org.name, 'skopbot');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Mirroring&setup=true`,
      );

      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Fill required fields first so only skopeo validation blocks submit
      await fillRequiredFields(authenticatedPage, robot.fullName, {
        namespace: 'testns',
      });

      // Set skopeo timeout below minimum (29)
      await authenticatedPage.getByTestId('skopeo-timeout-input').fill('29');

      // Verify validation error appears
      await expect(
        authenticatedPage.getByText('Minimum timeout is 30 seconds'),
      ).toBeVisible();

      // Submit button should be disabled
      await expect(
        authenticatedPage.getByTestId('submit-button'),
      ).toBeDisabled();

      // Set skopeo timeout above maximum (3601)
      await authenticatedPage.getByTestId('skopeo-timeout-input').fill('3601');

      // Verify validation error appears
      await expect(
        authenticatedPage.getByText('Maximum timeout is 3600 seconds (1 hour)'),
      ).toBeVisible();

      // Set valid value
      await authenticatedPage.getByTestId('skopeo-timeout-input').fill('300');

      // Verify validation error is gone
      await expect(
        authenticatedPage.getByText('Minimum timeout is 30 seconds'),
      ).not.toBeVisible();
      await expect(
        authenticatedPage.getByText('Maximum timeout is 3600 seconds (1 hour)'),
      ).not.toBeVisible();
    });

    test('validates sync interval is a positive number', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrival');
      const robot = await api.robot(org.name, 'ivalbot');

      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Mirroring&setup=true`,
      );

      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Clear the sync interval (it has default value)
      await authenticatedPage.getByTestId('sync-interval-input').fill('');

      // Verify validation error appears
      await expect(
        authenticatedPage.getByText('This field is required').first(),
      ).toBeVisible();

      // Fill with a valid value
      await authenticatedPage.getByTestId('sync-interval-input').fill('60');

      // Error should be resolved for the interval
      const intervalErrors = authenticatedPage
        .locator('[id="sync_interval"]')
        .locator('..');
      await expect(
        intervalErrors.getByText('Must be a positive number'),
      ).not.toBeVisible();
    });

    test('cancel delete modal keeps config intact', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrkeep');
      const robot = await api.robot(org.name, 'keepbot');

      // Create config via API
      const syncStartDate = new Date();
      syncStartDate.setMinutes(syncStartDate.getMinutes() + 5);
      await api.raw.createOrgMirrorConfig(org.name, {
        external_registry_type: 'quay',
        external_registry_url: 'https://quay.io',
        external_namespace: 'projectquay',
        robot_username: robot.fullName,
        visibility: 'private',
        sync_interval: 3600,
        sync_start_date: syncStartDate.toISOString().replace(/\.\d{3}Z$/, 'Z'),
      });

      await authenticatedPage.goto(`/organization/${org.name}?tab=Mirroring`);

      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();

      // Click delete button
      await authenticatedPage.getByTestId('delete-mirror-button').click();

      // Verify confirmation modal appears
      await expect(
        authenticatedPage
          .getByText(
            'Are you sure you want to delete the organization mirror configuration?',
          )
          .first(),
      ).toBeVisible();

      // Click Cancel instead of confirm
      await authenticatedPage.getByRole('button', {name: 'Cancel'}).click();

      // Modal should be closed
      await expect(
        authenticatedPage
          .getByText(
            'Are you sure you want to delete the organization mirror configuration?',
          )
          .first(),
      ).not.toBeVisible();

      // Config should still exist
      const config = await api.raw.getOrgMirrorConfig(org.name);
      expect(config).not.toBeNull();

      // Form should still be visible
      await expect(
        authenticatedPage.getByTestId('org-mirror-form'),
      ).toBeVisible();
    });
  },
);
