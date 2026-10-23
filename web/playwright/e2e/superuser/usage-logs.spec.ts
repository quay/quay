import {test, expect} from '../../fixtures';

test.describe(
  'Superuser Usage Logs',
  {tag: ['@superuser', '@feature:SUPERUSERS_FULL_ACCESS']},
  () => {
    // Access control tests are covered by framework.spec.ts

    test('displays usage logs page with columns', async ({superuserPage}) => {
      await superuserPage.goto('/usage-logs');

      // Verify page header
      await expect(
        superuserPage.getByRole('heading', {name: 'Usage Logs'}),
      ).toBeVisible();

      // Verify date range pickers exist
      await expect(superuserPage.getByText('From:')).toBeVisible();
      await expect(superuserPage.getByText('To:')).toBeVisible();

      // Verify table columns (superuser has Namespace column)
      await expect(
        superuserPage.getByRole('columnheader', {name: 'Date & Time'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('columnheader', {name: 'Description'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('columnheader', {name: 'Namespace'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('columnheader', {name: 'Performed by'}),
      ).toBeVisible();
      await expect(
        superuserPage.getByRole('columnheader', {name: 'IP Address'}),
      ).toBeVisible();

      // Verify table is present
      await expect(superuserPage.getByTestId('usage-logs-table')).toBeVisible();

      // Verify chart toggle exists
      await expect(
        superuserPage.getByTestId('usage-logs-chart-toggle'),
      ).toBeVisible();
    });

    test('toggles chart visibility', async ({superuserPage}) => {
      await superuserPage.goto('/usage-logs');

      // Wait for page to load
      await expect(superuserPage.getByTestId('usage-logs-table')).toBeVisible();

      // Toggle chart off
      await superuserPage.getByTestId('usage-logs-chart-toggle').click();
      await expect(
        superuserPage.getByTestId('usage-logs-chart-toggle'),
      ).toContainText('Show Chart');

      // Toggle chart back on
      await superuserPage.getByTestId('usage-logs-chart-toggle').click();
      await expect(
        superuserPage.getByTestId('usage-logs-chart-toggle'),
      ).toContainText('Hide Chart');
    });

    test('filters logs in the table', async ({superuserPage}) => {
      await superuserPage.goto('/usage-logs');

      // Wait for table to load
      await expect(superuserPage.getByTestId('usage-logs-table')).toBeVisible();

      // Wait for filter input to be available
      await expect(superuserPage.getByPlaceholder('Filter logs')).toBeVisible();

      // Filter by some text (any text that might appear in logs)
      await superuserPage.getByPlaceholder('Filter logs').fill('user');

      // Verify filter was applied (input has value)
      await expect(superuserPage.getByPlaceholder('Filter logs')).toHaveValue(
        'user',
      );

      // The table should still be visible
      await expect(superuserPage.getByTestId('usage-logs-table')).toBeVisible();
    });

    test('chart legend labels are not truncated', async ({superuserPage}) => {
      await superuserPage.goto('/usage-logs');

      // Ensure the chart is visible
      const toggle = superuserPage.getByTestId('usage-logs-chart-toggle');
      await expect(toggle).toBeVisible();
      if ((await toggle.textContent())?.includes('Show Chart')) {
        await toggle.click();
      }

      // Wait for chart to render
      const chart = superuserPage.getByTestId('usage-logs-chart');
      await expect(chart).toBeVisible();

      // Verify the legend container does not clip its content horizontally
      const container = superuserPage.locator('.usage-logs-legend-container');
      await expect(container).toBeVisible();
      const box = await container.boundingBox();
      if (box) {
        // scrollWidth should not exceed clientWidth (no hidden overflow)
        const overflow = await container.evaluate((el) => {
          return el.scrollWidth > el.clientWidth;
        });
        expect(overflow).toBe(false);
      }
    });

    test('shows info alert when Splunk search is not configured', async ({
      superuserPage,
    }) => {
      await superuserPage.route('**/api/v1/superuser/logs*', async (route) => {
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
      });
      await superuserPage.route(
        '**/api/v1/superuser/aggregatelogs*',
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

      await superuserPage.goto('/usage-logs');

      await expect(
        superuserPage
          .getByText(
            'Audit log viewing requires a search_token to be configured for Splunk HEC.',
          )
          .first(),
      ).toBeVisible();
    });
  },
);
