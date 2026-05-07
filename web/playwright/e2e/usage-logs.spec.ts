import {test, expect} from '../fixtures';
import type {Page} from '@playwright/test';

async function assertChartLegend(
  page: Page,
  orgName: string,
  legends: string[],
  chartTestId = 'usage-logs-chart',
): Promise<void> {
  await page.goto(`/organization/${orgName}?tab=Logs`);
  const chart = page.getByTestId(chartTestId);
  await expect(chart).toBeVisible();
  for (const text of legends) {
    await expect(chart.getByText(text, {exact: true})).toBeVisible();
  }
}

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

  test.describe('chart log kind mapping', {tag: ['@PROJQUAY-11079']}, () => {
    test(
      'quota log kinds appear in the chart legend',
      {tag: ['@feature:QUOTA_MANAGEMENT', '@feature:EDIT_QUOTA']},
      async ({superuserPage, superuserApi}) => {
        const org = await superuserApi.organization('chartquota');
        // org_create_quota
        const quota = await superuserApi.quota(org.name, 100 * 1024 * 1024);
        // org_change_quota
        await superuserApi.raw.updateOrganizationQuota(
          org.name,
          quota.quotaId,
          200 * 1024 * 1024,
        );
        // org_create_quota_limit
        await superuserApi.raw.createQuotaLimit(
          org.name,
          quota.quotaId,
          'Warning',
          80,
        );
        // Fetch updated quota to get the new limit ID
        const quotas = await superuserApi.raw.getOrganizationQuota(org.name);
        const limitId = quotas[0].limits[0].id;
        // org_change_quota_limit
        await superuserApi.raw.changeOrganizationQuotaLimit(
          org.name,
          quota.quotaId,
          limitId,
          'Warning',
          90,
        );
        // org_delete_quota_limit
        await superuserApi.raw.deleteQuotaLimit(
          org.name,
          quota.quotaId,
          limitId,
        );
        // org_delete_quota
        await superuserApi.raw.deleteOrganizationQuota(org.name, quota.quotaId);

        await assertChartLegend(superuserPage, org.name, [
          'Create Organization Quota',
          'Change Organization Quota',
          'Create Organization Quota Limit',
          'Change Organization Quota Limit',
          'Delete Organization Quota Limit',
          'Delete Organization Quota',
        ]);
      },
    );

    test('robot federation log kinds appear in the chart legend', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('chartfed');
      const robot = await api.robot(org.name, 'chartfedbot');
      // create_robot_federation
      await api.raw.createRobotFederation(org.name, robot.shortname, [
        {
          issuer: 'https://token.actions.githubusercontent.com',
          subject: 'repo:testorg/testrepo:ref:refs/heads/main',
        },
      ]);
      // delete_robot_federation
      // (federated_robot_token_exchange is not triggered here — it requires
      // a real OIDC token exchange with an external issuer, which is not
      // feasible in a CI environment)
      await api.raw.deleteRobotFederation(org.name, robot.shortname);

      await assertChartLegend(authenticatedPage, org.name, [
        'Create Robot Federation',
        'Delete Robot Federation',
      ]);
    });
  });
});

test.describe(
  'Usage Logs Repository column namespace deduplication',
  {tag: ['@logs', '@PROJQUAY-10605']},
  () => {
    // Escape special regex characters in generated names (e.g. dots, plus signs)
    const escapeRegex = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

    test(
      'superuser view shows only repo name in Repository column (not namespace/repo)',
      {tag: '@superuser'},
      async ({superuserPage, superuserApi}) => {
        // Creating a repo generates a real create_repo log with {namespace, repo} metadata
        const repo = await superuserApi.repository();
        const orgName = repo.fullName.split('/')[0];
        const repoName = repo.fullName.split('/')[1];

        // Superuser usage logs page — isSuperuser=true, shows Namespace + Repository columns
        await superuserPage.goto('/usage-logs');

        const table = superuserPage.getByTestId('usage-logs-table');
        await expect(table).toBeVisible();

        // Filter to find our specific log entry
        await superuserPage.getByPlaceholder('Filter logs').fill(repoName);
        await superuserPage.waitForTimeout(500);

        // Scope to td cells with exact text to avoid matching Description column.
        // Escape regex metacharacters in case generated names contain them.
        const repoNameCell = table
          .locator('td')
          .filter({hasText: new RegExp(`^${escapeRegex(repoName)}$`)});
        await expect(repoNameCell.first()).toBeVisible();
        await expect(
          table.locator('td').filter({
            hasText: new RegExp(
              `^${escapeRegex(orgName)}/${escapeRegex(repoName)}$`,
            ),
          }),
        ).not.toBeVisible();
      },
    );

    test('non-superuser view shows full namespace/repo in Repository column', async ({
      authenticatedPage,
      api,
    }) => {
      // Creating a repo generates a real create_repo log with {namespace, repo} metadata
      const repo = await api.repository();
      const orgName = repo.fullName.split('/')[0];
      const repoName = repo.fullName.split('/')[1];

      // Org-level logs — isSuperuser=false, no Namespace column, Repository shows full path
      await authenticatedPage.goto(`/organization/${orgName}?tab=Logs`);

      const table = authenticatedPage.getByTestId('usage-logs-table');
      await expect(table).toBeVisible();

      // Filter to find the create_repo log entry
      await authenticatedPage.getByPlaceholder('Filter logs').fill(repoName);
      await authenticatedPage.waitForTimeout(500);

      // Scope to td cells with exact text. Use .first() to avoid strict mode
      // violation if multiple log rows exist for the same repo.
      await expect(
        table
          .locator('td')
          .filter({
            hasText: new RegExp(
              `^${escapeRegex(orgName)}/${escapeRegex(repoName)}$`,
            ),
          })
          .first(),
      ).toBeVisible();
    });
  },
);
