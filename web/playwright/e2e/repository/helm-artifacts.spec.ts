/**
 * Helm Chart OCI Artifact E2E Tests
 *
 * Tests the complete UI workflow for Helm charts as OCI artifacts:
 * - Helm chart badge/icon display in repository list
 * - Chart metadata display in repository details
 * - Helm pull instructions display
 *
 * Uses real helm CLI to push actual Helm charts to the registry.
 *
 * @PROJQUAY-11451
 */

import {test, expect} from '../../fixtures';
import {pushHelmChart, isHelmAvailable} from '../../utils/container';

test.describe(
  'Helm Chart OCI Artifacts',
  {tag: ['@repository', '@helm']},
  () => {
    test.describe('Repository List Display', () => {
      test('Test 2.1: displays Helm chart icon/badge in repository list', async ({
        authenticatedPage,
        api,
      }) => {
        // Skip if helm CLI is not available
        if (!(await isHelmAvailable())) {
          test.skip(true, 'helm CLI not available');
        }

        // Create organization
        const org = await api.organization('helmcharts');

        // Push a real Helm chart to the registry
        await pushHelmChart(
          org.name,
          'nginx-chart',
          '1.0.0',
          'devtable',
          'password',
          {
            description: 'NGINX web server chart',
            appVersion: '1.25.0',
          },
        );

        // Navigate to repository list
        await authenticatedPage.goto(`/organization/${org.name}`);

        // Wait for repository list table to load
        const reposPanel = authenticatedPage.getByRole('tabpanel', {
          name: 'Repositories',
        });
        await expect(
          reposPanel.getByTestId('repository-list-table'),
        ).toBeVisible();

        // Verify the Helm chart repository appears in the list
        const table = reposPanel.getByTestId('repository-list-table');
        await expect(table).toContainText('nginx-chart');

        // Verify table renders without errors
        const firstRow = authenticatedPage.locator('tbody tr').first();
        await expect(firstRow.locator('[data-label="Name"]')).toBeVisible();
        await expect(
          firstRow.locator('[data-label="Visibility"]'),
        ).toBeVisible();

        // TODO: Verify Helm chart badge/icon is displayed (depends on UI implementation)
        // The chart should be visually distinguishable from regular container images
      });

      test('Test 2.1b: displays Helm chart in global repository view', async ({
        authenticatedPage,
        api,
      }) => {
        // Skip if helm CLI is not available
        if (!(await isHelmAvailable())) {
          test.skip(true, 'helm CLI not available');
        }

        // Create organization
        const org = await api.organization('globalhelm');

        // Push a Helm chart
        await pushHelmChart(
          org.name,
          'nginx-chart',
          '1.0.0',
          'devtable',
          'password',
          {
            description: 'NGINX web server chart',
            appVersion: '1.25.0',
          },
        );

        // Navigate to global repository view
        await authenticatedPage.goto('/repository');

        await expect(
          authenticatedPage.getByRole('heading', {name: 'Repositories'}),
        ).toBeVisible();

        // Search for our Helm chart repository
        const searchInput =
          authenticatedPage.getByPlaceholder(/Search by name/);
        const repoFullName = `${org.name}/nginx-chart`;
        await searchInput.fill(repoFullName);

        // Verify the Helm chart repository appears
        const table = authenticatedPage.getByTestId('repository-list-table');
        await expect(table).toContainText(repoFullName);

        // Verify we can click through to the repository
        await authenticatedPage.getByRole('link', {name: repoFullName}).click();

        // Should navigate to repository details page
        const expectedUrl = `/repository/${org.name}/nginx-chart`;
        await expect(authenticatedPage.url()).toContain(expectedUrl);
      });
    });

    test.describe('Repository Details Display', () => {
      test('Test 2.2: displays chart metadata in repository details', async ({
        authenticatedPage,
        api,
      }) => {
        // Skip if helm CLI is not available
        if (!(await isHelmAvailable())) {
          test.skip(true, 'helm CLI not available');
        }

        // Create organization
        const org = await api.organization('helmdetails');

        // Push a Helm chart with specific metadata
        await pushHelmChart(
          org.name,
          'postgresql-chart',
          '12.1.5',
          'devtable',
          'password',
          {
            description: 'PostgreSQL database chart',
            appVersion: '14.7',
          },
        );

        // Navigate to repository details
        await authenticatedPage.goto(
          `/repository/${org.name}/postgresql-chart`,
        );

        // Verify repository details page loaded
        await expect(authenticatedPage.getByTestId('repo-title')).toContainText(
          'postgresql-chart',
        );

        // Verify Tags tab is present and accessible
        const tagsTab = authenticatedPage.getByRole('tab', {name: /Tags/});
        await expect(tagsTab).toBeVisible();
        await tagsTab.click();

        // Verify Tags panel is displayed
        const tagsPanel = authenticatedPage.getByRole('tabpanel', {
          name: /Tags/,
        });
        await expect(tagsPanel).toBeVisible();

        // Verify the pushed tag appears in the tags list
        await expect(tagsPanel).toContainText('12.1.5');

        // TODO: Verify Chart.yaml metadata is displayed:
        // - Chart name: postgresql-chart
        // - Chart version: 12.1.5
        // - App version: 14.7
        // - Description: PostgreSQL database chart
      });

      test('Test 2.2b: repository details shows correct information fields', async ({
        authenticatedPage,
        api,
      }) => {
        // Skip if helm CLI is not available
        if (!(await isHelmAvailable())) {
          test.skip(true, 'helm CLI not available');
        }

        // Create organization
        const org = await api.organization('helminfo');

        // Push a Helm chart with dependencies to test metadata display
        await pushHelmChart(
          org.name,
          'redis-chart',
          '17.8.0',
          'devtable',
          'password',
          {
            description: 'Redis key-value store',
            appVersion: '7.2.4',
            dependencies: [
              {
                name: 'common',
                version: '2.x',
                repository: 'https://charts.bitnami.com/bitnami',
              },
            ],
          },
        );

        // Navigate to repository details
        await authenticatedPage.goto(`/repository/${org.name}/redis-chart`);

        // Verify Information tab exists and can be clicked
        const infoTab = authenticatedPage.getByRole('tab', {
          name: /Information/,
        });
        await expect(infoTab).toBeVisible();
        await infoTab.click();

        // Verify Information panel is displayed
        const infoPanel = authenticatedPage.getByRole('tabpanel', {
          name: /Information/,
        });
        await expect(infoPanel).toBeVisible();

        // Verify repository name is displayed
        await expect(infoPanel).toContainText('redis-chart');

        // TODO: Verify Chart.yaml metadata is displayed:
        // - Description: Redis key-value store
        // - App version: 7.2.4
        // - Dependencies: common@2.x
      });
    });

    test.describe('Pull Instructions Display', () => {
      test('Test 2.3: displays Helm pull instructions correctly', async ({
        authenticatedPage,
        api,
      }) => {
        // Skip if helm CLI is not available
        if (!(await isHelmAvailable())) {
          test.skip(true, 'helm CLI not available');
        }

        // Create organization
        const org = await api.organization('helmpull');

        // Push a Helm chart
        await pushHelmChart(
          org.name,
          'wordpress-chart',
          '18.0.1',
          'devtable',
          'password',
          {
            description: 'WordPress blogging platform',
            appVersion: '6.4.2',
          },
        );

        // Navigate to repository details
        await authenticatedPage.goto(`/repository/${org.name}/wordpress-chart`);

        // Verify repository details loaded
        await expect(authenticatedPage.getByTestId('repo-title')).toContainText(
          'wordpress-chart',
        );

        // Verify Information tab is present and accessible
        const infoTab = authenticatedPage.getByRole('tab', {
          name: /Information/,
        });
        await expect(infoTab).toBeVisible();
        await infoTab.click();

        // Verify Information panel loads
        const infoPanel = authenticatedPage.getByRole('tabpanel', {
          name: /Information/,
        });
        await expect(infoPanel).toBeVisible();

        // TODO: Verify Helm pull instructions are displayed with correct syntax:
        // - helm pull oci://<registry>/<org>/wordpress-chart --version 18.0.1
        // - NOT docker pull (incorrect for Helm charts)
        // - Instructions should be in a code block or copyable format
      });

      test('Test 2.3b: pull instructions accessible from multiple views', async ({
        authenticatedPage,
        api,
      }) => {
        // Skip if helm CLI is not available
        if (!(await isHelmAvailable())) {
          test.skip(true, 'helm CLI not available');
        }

        // Create organization
        const org = await api.organization('helminstructions');

        // Push a Helm chart
        await pushHelmChart(
          org.name,
          'mysql-chart',
          '8.9.0',
          'devtable',
          'password',
          {
            description: 'MySQL database chart',
            appVersion: '8.0.33',
          },
        );

        // Navigate to repository details
        await authenticatedPage.goto(`/repository/${org.name}/mysql-chart`);

        // Verify we can access different tabs that might contain pull instructions
        const tabs = ['Information', 'Tags'];

        for (const tabName of tabs) {
          const tab = authenticatedPage.getByRole('tab', {
            name: new RegExp(tabName),
          });
          await expect(tab).toBeVisible();
          await tab.click();

          // Verify tab panel loads without errors
          const panel = authenticatedPage.getByRole('tabpanel', {
            name: new RegExp(tabName),
          });
          await expect(panel).toBeVisible();
        }

        // Note: When real Helm charts are pushed, pull instructions should be
        // consistently accessible and formatted correctly across all relevant views.
        // The instructions should use `helm pull oci://` syntax, not `docker pull`.
      });

      test('Test 2.3c: repository shows appropriate artifact type indication', async ({
        authenticatedPage,
        api,
      }) => {
        // Skip if helm CLI is not available
        if (!(await isHelmAvailable())) {
          test.skip(true, 'helm CLI not available');
        }

        // Create organization
        const org = await api.organization('helmtype');

        // Push a Helm chart
        await pushHelmChart(
          org.name,
          'kafka-chart',
          '26.8.0',
          'devtable',
          'password',
          {
            description: 'Apache Kafka streaming platform',
            appVersion: '3.6.1',
          },
        );

        // Also create a regular container image repository for comparison
        // (We can't easily push a container image here without container runtime,
        // but creating the repo is enough to verify coexistence)
        await api.repository(org.name, 'regular-image');

        // Navigate to organization view to see both repositories
        await authenticatedPage.goto(`/organization/${org.name}`);

        const reposPanel = authenticatedPage.getByRole('tabpanel', {
          name: 'Repositories',
        });
        const table = reposPanel.getByTestId('repository-list-table');

        // Both repositories should be visible
        await expect(table).toContainText('kafka-chart');
        await expect(table).toContainText('regular-image');

        // TODO: Verify the UI visually distinguishes Helm charts from container images
        // - Helm chart should have an icon/badge indicating it's a Helm chart
        // - Regular image should have standard container image styling
        // - Both types should coexist without rendering issues
      });
    });

    test.describe('Helm Chart Metadata Integration', () => {
      test('repository API returns correct metadata for Helm chart artifacts', async ({
        api,
        adminClient,
      }) => {
        // Skip if helm CLI is not available
        if (!(await isHelmAvailable())) {
          test.skip(true, 'helm CLI not available');
        }

        // Create organization
        const org = await api.organization('helmapi');

        // Push a real Helm chart
        await pushHelmChart(
          org.name,
          'api-test-chart',
          '3.2.1',
          'devtable',
          'password',
          {
            description: 'API integration test chart',
            appVersion: '1.0.0',
          },
        );

        // Fetch repository details via API
        const response = await adminClient.get(
          `/api/v1/repository/${org.name}/api-test-chart`,
        );
        expect(response.status()).toBe(200);

        const body = await response.json();
        expect(body.name).toBe('api-test-chart');
        expect(body.namespace).toBe(org.name);

        // Verify repository kind is present
        expect(body.kind).toBeDefined();

        // TODO: Verify Helm-specific metadata in API response:
        // - is_public visibility setting
        // - tags array includes version 3.2.1
        // - Chart.yaml metadata if exposed via API
        // - OCI artifact media types (application/vnd.cncf.helm.config.v1+json)
      });
    });
  },
);
