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
  'Usage Logs Load More behavior',
  {tag: ['@logs', '@PROJQUAY-10795']},
  () => {
    test('shows spinner instead of button while fetching next page', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('loadmore');

      let callCount = 0;
      await authenticatedPage.route(
        `**/api/v1/organization/${org.name}/logs*`,
        async (route) => {
          callCount++;
          if (callCount === 1) {
            // First page — returns next_page token so hasNextPage=true
            // The hook maps response.data.next_page -> nextPage for getNextPageParam
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({
                logs: Array.from({length: 5}, (_, i) => ({
                  kind: 'push_repo',
                  datetime: new Date(Date.now() - i * 1000).toISOString(),
                  metadata: {namespace: org.name, repo: `repo${i}`},
                  performer: {name: 'testuser'},
                  ip: '127.0.0.1',
                })),
                next_page: 'page2token',
              }),
            });
          } else {
            // Second page — delay to allow spinner observation
            await new Promise((r) => setTimeout(r, 2000));
            await route.fulfill({
              status: 200,
              contentType: 'application/json',
              body: JSON.stringify({logs: []}),
            });
          }
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

      const table = authenticatedPage.getByTestId('usage-logs-table');
      await expect(table).toBeVisible();

      // Load More button should be visible when there is a next page
      await expect(
        authenticatedPage.getByTestId('load-more-button'),
      ).toBeVisible();

      // Click Load More to trigger second page fetch
      await authenticatedPage.getByTestId('load-more-button').click();

      // While fetching, spinner should be visible and button should not be
      await expect(
        authenticatedPage.getByTestId('load-more-spinner'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('load-more-button'),
      ).not.toBeVisible();
    });

    test('Load More button appears when next page is available', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('loadmorebtn');

      await authenticatedPage.route(
        `**/api/v1/organization/${org.name}/logs*`,
        async (route) => {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              logs: [
                {
                  kind: 'push_repo',
                  datetime: new Date().toISOString(),
                  metadata: {namespace: org.name, repo: 'myimage'},
                  performer: {name: 'testuser'},
                  ip: '127.0.0.1',
                },
              ],
              next_page: 'sometoken',
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
      await expect(
        authenticatedPage.getByTestId('usage-logs-table'),
      ).toBeVisible();

      // Load More button should be visible when next_page token exists
      await expect(
        authenticatedPage.getByTestId('load-more-button'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByTestId('load-more-spinner'),
      ).not.toBeVisible();
    });
  },
);
