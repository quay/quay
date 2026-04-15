import {test, expect} from '../fixtures';
import {pushImage} from '../utils/container';
import {TEST_USERS} from '../global-setup';

test.describe('Usage Logs', {tag: ['@logs']}, () => {
  test('displays organization usage logs with chart and table', async ({
    authenticatedPage,
    api,
  }) => {
    // Create org to ensure logs exist (org_create log will be generated)
    const org = await api.organization('logs');

    await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);

    // Verify table exists
    await expect(
      authenticatedPage.getByTestId('usage-logs-table'),
    ).toBeVisible();

    // Verify chart toggle button exists
    await expect(
      authenticatedPage.getByTestId('usage-logs-chart-toggle'),
    ).toBeVisible();
  });

  test('toggles chart visibility', async ({authenticatedPage, api}) => {
    const org = await api.organization('charttoggle');

    await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);

    // Wait for page to load
    await expect(
      authenticatedPage.getByTestId('usage-logs-table'),
    ).toBeVisible();

    // Chart may or may not be visible initially depending on data
    // Click toggle to hide chart
    await authenticatedPage.getByTestId('usage-logs-chart-toggle').click();

    // Verify button text changed to "Show Chart"
    await expect(
      authenticatedPage.getByTestId('usage-logs-chart-toggle'),
    ).toContainText('Show Chart');

    // Click toggle to show chart
    await authenticatedPage.getByTestId('usage-logs-chart-toggle').click();

    // Verify button text changed back to "Hide Chart"
    await expect(
      authenticatedPage.getByTestId('usage-logs-chart-toggle'),
    ).toContainText('Hide Chart');
  });

  test('exports repository logs', async ({authenticatedPage, api}) => {
    const repo = await api.repository();

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=logs`);

    await authenticatedPage.getByTestId('usage-logs-export-button').click();
    await authenticatedPage
      .getByTestId('usage-logs-export-email-input')
      .fill('test@example.com');
    await authenticatedPage
      .getByTestId('usage-logs-export-confirm-button')
      .click();

    await expect(
      authenticatedPage.getByText('Logs exported with id'),
    ).toBeVisible();
  });

  test('validates export email input', async ({authenticatedPage, api}) => {
    const repo = await api.repository();

    await authenticatedPage.goto(`/repository/${repo.fullName}?tab=logs`);

    await authenticatedPage.getByTestId('usage-logs-export-button').click();
    await authenticatedPage
      .getByTestId('usage-logs-export-email-input')
      .fill('invalid-email');

    await expect(
      authenticatedPage.getByTestId('usage-logs-export-confirm-button'),
    ).toBeDisabled();
  });

  test('filters logs by text input', async ({authenticatedPage, api}) => {
    const org = await api.organization('filter');

    await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);

    // Wait for table and scroll it into view
    const table = authenticatedPage.getByTestId('usage-logs-table');
    await table.scrollIntoViewIfNeeded();
    await expect(table).toBeVisible();

    // Wait for logs to load by checking for the filter input
    await expect(
      authenticatedPage.getByPlaceholder('Filter logs'),
    ).toBeVisible();

    // Filter by "created" to match the "Organization xxx created" log entry
    await authenticatedPage.getByPlaceholder('Filter logs').fill('created');

    // Give filter time to apply
    await authenticatedPage.waitForTimeout(500);

    // Verify filtered results show the organization created log
    await expect(
      authenticatedPage.getByTestId('usage-logs-table').getByText(/created/),
    ).toBeVisible();
  });

  test('displays org mirror sync failure with stderr details', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('mirrstderr');

    // Mock logs API to return an org_mirror_sync_failed log with stderr
    await authenticatedPage.route(
      `**/api/v1/organization/${org.name}/logs*`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            logs: [
              {
                kind: 'org_mirror_sync_failed',
                datetime: new Date().toISOString(),
                metadata: {
                  message:
                    "Sync failed for 'quay.io/projectquay/quay': 2/2 tags failed",
                  stderr:
                    '[v1.0]: skopeo: authentication required; [v2.0]: skopeo: manifest unknown',
                },
                performer: {name: 'mirror-robot'},
                ip: '127.0.0.1',
              },
            ],
          }),
        });
      },
    );
    await authenticatedPage.route(
      `**/api/v1/organization/${org.name}/aggregatelogs*`,
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({aggregated: []}),
        });
      },
    );

    await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);

    // Verify the table renders the failure log with stderr content
    const table = authenticatedPage.getByTestId('usage-logs-table');
    await expect(table).toBeVisible();

    await expect(table.getByText(/Sync failed for/)).toBeVisible();
    await expect(
      table.getByText(/skopeo: authentication required/),
    ).toBeVisible();
  });

  test.describe(
    'chart log kind mapping',
    {tag: ['@PROJQUAY-11079', '@feature:QUOTA_MANAGEMENT']},
    () => {
      test(
        'org_create_quota and org_change_quota appear in the chart legend',
        {tag: ['@feature:EDIT_QUOTA']},
        async ({authenticatedPage, api}) => {
          const org = await api.organization('chartquota');
          // Create quota → logs org_create_quota
          const quota = await api.quota(org.name, 100 * 1024 * 1024);
          // Update quota → logs org_change_quota
          await api.raw.updateOrganizationQuota(
            org.name,
            quota.quotaId,
            200 * 1024 * 1024,
          );

          await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);

          const chart = authenticatedPage.getByTestId('usage-logs-chart');
          await expect(chart).toBeVisible();
          await expect(
            chart.getByText('Create Organization Quota'),
          ).toBeVisible();
          await expect(
            chart.getByText('Change Organization Quota'),
          ).toBeVisible();
        },
      );

      test(
        'create_robot_federation appears in the chart legend',
        async ({authenticatedPage, api}) => {
          const org = await api.organization('chartfed');
          const robot = await api.robot(org.name, 'chartfedbot');
          // Create robot federation → logs create_robot_federation
          await api.raw.createRobotFederation(org.name, robot.shortname, [
            {issuer: 'https://token.actions.githubusercontent.com', subject: 'repo:testorg/testrepo:ref:refs/heads/main'},
          ]);

          await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);

          const chart = authenticatedPage.getByTestId('usage-logs-chart');
          await expect(chart).toBeVisible();
          await expect(
            chart.getByText('Create Robot Federation'),
          ).toBeVisible();
        },
      );

      test(
        'change_tag_immutability appears in the chart legend',
        {tag: ['@container']},
        async ({authenticatedPage, api}) => {
          const org = await api.organization('chartimmut');
          const repo = await api.repository(org.name, 'chartimmutrepo');

          // Push an image to create a tag, then set it immutable
          await pushImage(
            org.name,
            repo.name,
            'v1.0.0',
            TEST_USERS.user.username,
            TEST_USERS.user.password,
          );
          // Set tag immutable → logs change_tag_immutability
          await api.raw.setTagImmutability(
            org.name,
            repo.name,
            'v1.0.0',
            true,
          );

          await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);

          const chart = authenticatedPage.getByTestId('usage-logs-chart');
          await expect(chart).toBeVisible();
          await expect(
            chart.getByText('Change tag immutability'),
          ).toBeVisible();
        },
      );
    },
  );

  test('shows info alert when Splunk search is not configured', async ({
    authenticatedPage,
    api,
  }) => {
    const org = await api.organization('splunk');

    // Mock 200 response with search_unavailable flag
    await authenticatedPage.route(
      '**/api/v1/organization/*/logs*',
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            logs: [],
            search_unavailable: true,
            message:
              'Audit log viewing requires a search_token to be configured for Splunk HEC.',
          }),
        });
      },
    );
    await authenticatedPage.route(
      '**/api/v1/organization/*/aggregatelogs*',
      async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            aggregated: [],
            search_unavailable: true,
            message:
              'Audit log viewing requires a search_token to be configured for Splunk HEC.',
          }),
        });
      },
    );

    await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);

    await expect(
      authenticatedPage
        .getByText(
          'Audit log viewing requires a search_token to be configured for Splunk HEC.',
        )
        .first(),
    ).toBeVisible();
  });
});
