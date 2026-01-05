import {test, expect} from '../../fixtures';

test.describe(
  'Superuser Usage Logs',
  {tag: ['@superuser', '@feature:SUPERUSERS_FULL_ACCESS']},
  () => {
    // Access control tests are covered by framework.spec.ts

    test('displays usage logs page with chart and table', async ({
      superuserPage,
    }) => {
      await superuserPage.goto('/usage-logs');

      // Verify page header
      await expect(
        superuserPage.getByRole('heading', {name: 'Usage Logs'}),
      ).toBeVisible();

      // Verify date range pickers exist
      await expect(superuserPage.getByText('From:')).toBeVisible();
      await expect(superuserPage.getByText('To:')).toBeVisible();
      await expect(
        superuserPage.getByLabel('Date picker').first(),
      ).toBeVisible();

      // Verify chart area is visible (either chart with data or "No data" message)
      // The Hide Chart button is always visible regardless of data
      await expect(
        superuserPage.getByRole('button', {name: 'Hide Chart'}),
      ).toBeVisible();

      // Toggle chart visibility - hide
      await superuserPage.getByRole('button', {name: 'Hide Chart'}).click();
      await expect(
        superuserPage.getByRole('button', {name: 'Show Chart'}),
      ).toBeVisible();

      // Toggle chart visibility - show again
      await superuserPage.getByRole('button', {name: 'Show Chart'}).click();
      await expect(
        superuserPage.getByRole('button', {name: 'Hide Chart'}),
      ).toBeVisible();

      // Verify table is present (may need to scroll and wait for async load)
      const table = superuserPage.getByTestId('usage-logs-table');
      await table.scrollIntoViewIfNeeded();
      await expect(table).toBeVisible({timeout: 15000});
    });

    test('filters logs in the table', async ({superuserPage}) => {
      await superuserPage.goto('/usage-logs');

      // Wait for table to load (may need to scroll and wait for async load)
      const table = superuserPage.getByTestId('usage-logs-table');
      await table.scrollIntoViewIfNeeded();
      await expect(table).toBeVisible({timeout: 15000});

      // Verify filter input exists and can be used
      const filterInput = superuserPage.getByPlaceholder('Filter logs');
      await expect(filterInput).toBeVisible();

      // Type in filter (test that it's functional)
      await filterInput.fill('create');
      // Filter is applied immediately - no button to click
      // The table should still be visible
      await expect(superuserPage.getByTestId('usage-logs-table')).toBeVisible();
    });
  },
);
