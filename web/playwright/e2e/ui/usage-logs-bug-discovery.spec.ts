import {test, expect} from '../../fixtures';

/**
 * Bug Discovery Tests: Usage Logs
 *
 * These tests reproduce potential UI bugs found via static analysis
 * of the UsageLogs component and related chart/date handling.
 */
test.describe(
  'Bug Discovery: Usage Logs',
  {tag: ['@bug-discovery', '@logs']},
  () => {
    test('chart toggle should not break date picker state', {
      tag: ['@repository'],
    }, async ({authenticatedPage, api}) => {
      // Bug: UsageLogs.tsx:38-41
      // The minDate and maxDate variables are recreated on every render using
      // new Date(). When the user toggles chart visibility, the component
      // re-renders and new Date objects are created. This means the date
      // validators reference fresh dates each render, which could cause
      // inconsistent validation near midnight.
      //
      // Additional concern: the useEffect at line 52-63 that invalidates
      // queries on date change is missing queryClient from its dependency array.
      //
      // Expected behavior: toggling chart does not affect date picker values
      // Actual behavior: dates should remain stable across re-renders

      const org = await api.organization('logsbug');

      // Navigate to org page and go to Logs tab
      await authenticatedPage.goto(
        `/organization/${org.name}?tab=Logs`,
      );

      // Wait for usage logs section to load
      const chartToggle = authenticatedPage.getByTestId(
        'usage-logs-chart-toggle',
      );
      await expect(chartToggle).toBeVisible();

      // Capture the initial date values from the date pickers
      // PatternFly DatePicker renders an input with the date value
      const datePickers = authenticatedPage.locator(
        'input[placeholder*="yyyy"]',
      );

      // There should be two date pickers (start and end)
      const datePickerCount = await datePickers.count();
      expect(datePickerCount).toBeGreaterThanOrEqual(2);

      // Get initial date values (these should be auto-populated)
      const startDate = await datePickers.nth(0).inputValue();
      const endDate = await datePickers.nth(1).inputValue();

      // Both dates should be populated (not empty)
      expect(startDate).toBeTruthy();
      expect(endDate).toBeTruthy();

      // Toggle chart off
      await chartToggle.click();
      await expect(chartToggle).toContainText('Show Chart');

      // Toggle chart back on
      await chartToggle.click();
      await expect(chartToggle).toContainText('Hide Chart');

      // Dates should remain the same after re-render
      await expect(datePickers.nth(0)).toHaveValue(startDate);
      await expect(datePickers.nth(1)).toHaveValue(endDate);
    });

    test('usage logs should load without errors for repository view', {
      tag: ['@repository'],
    }, async ({authenticatedPage, api}) => {
      // Bug: UsageLogsGraph.tsx:194-197
      // Chart bars use array index as key: key={index}
      // If log kinds appear in different order across re-renders (e.g., due
      // to Object.keys() ordering changing when new log types appear), React
      // will associate the wrong style/data with the wrong bar component.
      //
      // This test validates that the usage logs page loads without errors
      // and renders the chart toggle and date pickers correctly.
      //
      // Expected behavior: usage logs render with chart and table
      // Actual behavior: should work, but chart bars may animate incorrectly

      const repo = await api.repository(undefined, 'logsgraph');

      // Navigate to repository details, Logs tab
      await authenticatedPage.goto(
        `/repository/${repo.fullName}?tab=logs`,
      );

      // Verify the usage logs section renders
      const chartToggle = authenticatedPage.getByTestId(
        'usage-logs-chart-toggle',
      );
      await expect(chartToggle).toBeVisible();

      // Verify date pickers are present
      const datePickers = authenticatedPage.locator(
        'input[placeholder*="yyyy"]',
      );
      await expect(datePickers.nth(0)).toBeVisible();
      await expect(datePickers.nth(1)).toBeVisible();

      // Toggle chart visibility to exercise re-render path
      await chartToggle.click();
      await expect(chartToggle).toContainText('Show Chart');
      await chartToggle.click();
      await expect(chartToggle).toContainText('Hide Chart');

      // Page should remain functional (no React error boundary)
      await expect(authenticatedPage.getByText('Unable to')).not.toBeVisible();
    });
  },
);
