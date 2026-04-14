import {test, expect} from '../fixtures';

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

test.describe(
  'Usage Logs Load More button behavior',
  {tag: ['@logs', '@PROJQUAY-10795']},
  () => {
    test('shows Load More button when additional pages are available', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('loadmore');

      // Create 21 repos to generate 21 log entries — enough to trigger pagination (page size: 20)
      await Promise.all(
        Array.from({length: 21}, (_, i) =>
          api.repository(org.name, `repo${i}`),
        ),
      );

      await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);

      const table = authenticatedPage.getByTestId('usage-logs-table');
      await expect(table).toBeVisible();

      // With 21 log entries, the API returns a next_page token
      await expect(
        authenticatedPage.getByTestId('load-more-button'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('load-more-spinner'),
      ).not.toBeVisible();
    });

    test('shows spinner when Load More is clicked', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('loadmorespinner');

      // Create 21 repos to generate 21 real log entries
      await Promise.all(
        Array.from({length: 21}, (_, i) =>
          api.repository(org.name, `repo${i}`),
        ),
      );

      await authenticatedPage.goto(`/organization/${org.name}?tab=Logs`);
      const table = authenticatedPage.getByTestId('usage-logs-table');
      await expect(table).toBeVisible();

      // Load More button is visible because there are more than 20 logs
      const loadMoreBtn = authenticatedPage.getByTestId('load-more-button');
      await expect(loadMoreBtn).toBeVisible();

      // Delay the next-page response so the spinner stays visible long enough
      // to assert on. route.continue() passes through to the real API — no mocking.
      await authenticatedPage.route(
        `**/api/v1/organization/${org.name}/logs*`,
        async (route) => {
          await new Promise((resolve) => setTimeout(resolve, 500));
          await route.continue();
        },
      );

      // Click Load More — spinner should appear while fetching the next page
      await loadMoreBtn.click();

      await expect(
        authenticatedPage.getByTestId('load-more-spinner'),
      ).toBeVisible();
      await expect(loadMoreBtn).not.toBeVisible();
    });
  },
);
