/**
 * External Scripts Loading Tests (PROJQUAY-9803)
 *
 * Tests that external scripts (Stripe, StatusPage) are only loaded when BILLING feature is enabled.
 * This prevents 85-second delays in air-gapped/restricted network environments.
 */

import {test, expect, skipUnlessFeature} from '../../fixtures';

test.describe(
  'External Scripts Loading',
  {tag: ['@ui', '@PROJQUAY-9803']},
  () => {
    test.describe('BILLING Feature Disabled (Default)', () => {
      test('should NOT load Stripe or StatusPage scripts when BILLING is disabled', async ({
        authenticatedPage,
        quayConfig,
      }) => {
        // Skip this test if BILLING is enabled - we can't test "disabled" behavior in that environment
        test.skip(
          quayConfig?.features?.BILLING === true,
          'BILLING feature is enabled in this environment',
        );

        await authenticatedPage.goto('/');

        // Wait for page to fully load
        await authenticatedPage.waitForLoadState('networkidle');

        // Verify the Stripe script tag does not exist in the DOM
        await expect(
          authenticatedPage.locator('#stripe-checkout'),
        ).not.toBeAttached();

        // Verify the StatusPage script tag does not exist in the DOM
        await expect(
          authenticatedPage.locator('#statuspage-widget'),
        ).not.toBeAttached();

        // Verify no network requests were made to external domains via Performance API
        const externalRequests = await authenticatedPage.evaluate(() => {
          const resources = performance.getEntriesByType('resource');
          return resources.filter((entry) => {
            const name = entry.name;
            return (
              name.includes('stripe.com') || name.includes('statuspage.io')
            );
          }).length;
        });
        expect(externalRequests).toBe(0);
      });
    });

    test.describe('BILLING Feature Enabled', {tag: '@feature:BILLING'}, () => {
      test('should load Stripe and StatusPage scripts when BILLING is enabled', async ({
        authenticatedPage,
        quayConfig,
      }) => {
        test.skip(...skipUnlessFeature(quayConfig, 'BILLING'));

        await authenticatedPage.goto('/organization');

        // Wait for scripts to potentially load
        await authenticatedPage.waitForLoadState('networkidle');

        // Verify the Stripe script tag exists in the DOM
        const stripeScript = authenticatedPage.locator('#stripe-checkout');
        await expect(stripeScript).toBeAttached({timeout: 10000});
        await expect(stripeScript).toHaveAttribute('async', '');
        await expect(stripeScript).toHaveAttribute(
          'src',
          'https://checkout.stripe.com/checkout.js',
        );

        // Verify the StatusPage script tag exists in the DOM
        const statusPageScript =
          authenticatedPage.locator('#statuspage-widget');
        await expect(statusPageScript).toBeAttached({timeout: 10000});
        await expect(statusPageScript).toHaveAttribute('async', '');
        await expect(statusPageScript).toHaveAttribute(
          'src',
          'https://cdn.statuspage.io/se-v2.js',
        );
      });
    });
  },
);
