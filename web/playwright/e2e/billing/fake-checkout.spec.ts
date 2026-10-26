import {test, expect, uniqueName} from '../../fixtures/isolated-account';
import type {Plan} from '../../../src/resources/BillingResource';

test.describe(
  'Local simulated organization checkout',
  {tag: ['@organization', '@billing', '@feature:BILLING']},
  () => {
    test.skip(
      process.env.PLAYWRIGHT_FAKE_CHECKOUT !== 'true',
      'Requires the local FakeStripe provider.',
    );

    for (const complete of [false, true]) {
      test(`${
        complete ? 'completes' : 'cancels'
      } checkout after creating an organization in the same window`, async ({
        authenticatedPage: page,
        api,
      }) => {
        const name = uniqueName('checkout');
        const pageCount = page.context().pages().length;
        const {plans}: {plans: Plan[]} = await (
          await page.request.get('/api/v1/plans/')
        ).json();
        const plan = plans.find(
          (entry) =>
            entry.bus_features &&
            entry.price > 0 &&
            !entry.deprecated &&
            !entry.plans_page_hidden,
        );
        const creates: string[] = [];
        page.on('request', (request) => {
          if (
            request.method() === 'POST' &&
            new URL(request.url()).pathname === '/api/v1/organization/'
          )
            creates.push(request.url());
        });
        await page.goto('/organizations/new');
        await page.locator('#create-org-name-input').fill(name);
        await page.locator(`[id="organization-plan-${plan.stripeId}"]`).check();
        try {
          await page
            .getByRole('button', {name: 'Create and continue to checkout'})
            .click();
          await expect(page).toHaveURL(/\/fake-checkout\?/);
          await expect(
            page.getByRole('heading', {
              name: 'Simulated checkout',
              exact: true,
            }),
          ).toBeVisible();
          await expect(
            page.getByRole('heading', {name: `Subscribe to ${plan.title}`}),
          ).toBeVisible();
          await expect(
            page.getByText('No payment is collected.', {exact: false}),
          ).toBeVisible();
          await expect(page.getByRole('dialog')).toHaveCount(0);
          expect(page.context().pages()).toHaveLength(pageCount);
          expect(creates).toHaveLength(1);
          await page
            .getByRole('button', {
              name: complete ? 'Complete simulated checkout' : 'Cancel',
              exact: true,
            })
            .click();
          await expect(page).toHaveURL(new RegExp(`/organization/${name}\\?`));
          if (complete) {
            await expect(page.getByTestId('plan-change-result')).toContainText(
              'Your subscription has been updated.',
            );
            await expect(page.getByText('4242', {exact: false})).toBeVisible();
            await page.reload();
            await expect(page.getByTestId('plan-change-result')).toContainText(
              'Your subscription has been updated.',
            );
            await page
              .getByRole('button', {name: 'Change payment method', exact: true})
              .click();
            await expect(page).toHaveURL(/\/fake-checkout\?/);
            await expect(
              page.getByRole('heading', {
                name: 'Update payment method',
                exact: true,
              }),
            ).toBeVisible();
            await page
              .getByRole('button', {
                name: 'Complete simulated checkout',
                exact: true,
              })
              .click();
            await expect(page).toHaveURL(/paymentMethod=returned/);
            await expect(
              page.getByTestId('stored-payment-method'),
            ).toContainText('4242');
          } else {
            await expect(
              page.getByRole('heading', {name: /Stripe Checkout canceled/}),
            ).toBeVisible();
          }
          const subscription = await (
            await page.request.get(`/api/v1/organization/${name}/plan`)
          ).json();
          expect(subscription.hasSubscription).toBe(complete);
          expect(subscription.plan).toBe(complete ? plan.stripeId : 'free');
        } finally {
          await api.raw.deleteOrganization(name);
        }
      });
    }
  },
);
