/**
 * Overview page tests
 *
 * Tests the overview/landing page including expandable sections,
 * navigation buttons, tabs, and pricing plan selection.
 */

import {test, expect} from '../../fixtures';

test.describe(
  'Overview Page',
  {tag: ['@ui', '@overview', '@feature:BILLING']},
  () => {
    test('expandable dropdowns show content', async ({authenticatedPage}) => {
      await authenticatedPage.goto('/overview');

      // Store containers dropdown
      await authenticatedPage.getByTestId('store-containers-dropdown').click();
      await expect(
        authenticatedPage.getByTestId('store-containers-info'),
      ).toBeVisible();

      // Build containers dropdown
      await authenticatedPage.getByTestId('build-containers-dropdown').click();
      await expect(
        authenticatedPage.getByTestId('build-containers-info'),
      ).toBeVisible();

      // Scan containers dropdown
      await authenticatedPage.getByTestId('scan-containers-dropdown').click();
      await expect(
        authenticatedPage.getByTestId('scan-containers-info'),
      ).toBeVisible();

      // Public containers dropdown
      await authenticatedPage.getByTestId('public-containers-dropdown').click();
      await expect(
        authenticatedPage.getByTestId('public-containers-info'),
      ).toBeVisible();
    });

    test('external links navigate correctly', async ({authenticatedPage}) => {
      await authenticatedPage.goto('/overview');

      // Try Quay button navigates to organization page
      await authenticatedPage.getByTestId('try-quayio-button').click();
      await expect(authenticatedPage).toHaveURL(/.*\/organization/);

      // Go back to overview
      await authenticatedPage.goto('/overview');

      // Purchase button shows plans
      await authenticatedPage.getByTestId('purchase-quayio-button').click();
      await expect(
        authenticatedPage.getByTestId('purchase-plans'),
      ).toBeVisible();
    });

    test('tabs switch content correctly', async ({authenticatedPage}) => {
      await authenticatedPage.goto('/overview');

      // Click pricing tab
      await authenticatedPage
        .getByRole('tab', {name: 'Pricing and Features'})
        .click();
      await expect(
        authenticatedPage.getByTestId('purchase-plans'),
      ).toBeVisible();

      // Click overview tab
      await authenticatedPage.getByRole('tab', {name: 'Overview'}).click();
      await expect(
        authenticatedPage.getByTestId('store-containers-dropdown'),
      ).toBeVisible();
    });

    test('purchase plans dropdown shows pricing options', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.goto('/overview');

      // Navigate to pricing tab
      await authenticatedPage
        .getByRole('tab', {name: 'Pricing and Features'})
        .click();

      const options = [
        'plan-medium',
        'plan-large',
        'plan-XL',
        'plan-XXL',
        'plan-XXXL',
        'plan-XXXXL',
        'plan-XXXXXL',
      ];

      for (const option of options) {
        await authenticatedPage.getByTestId('plans-dropdown').click();
        await authenticatedPage.getByTestId(option).click();

        // Verify selected pricing and pricing value are visible after selection
        await expect(
          authenticatedPage.getByTestId('selected-pricing'),
        ).toBeVisible();
        await expect(
          authenticatedPage.getByTestId('pricing-value'),
        ).toBeVisible();
      }
    });
  },
);
