import {test, expect} from '@playwright/test';
import type {Plan} from '../../../src/resources/BillingResource';

test.describe(
  'Hosted Quay billing',
  {tag: ['@smoke', '@config:BILLING']},
  () => {
    test.skip(
      !process.env.QUAY_HOSTED_NAMESPACE,
      'Requires the hosted development profile and a designated namespace.',
    );

    test('reads the live catalog and billing summary through the local proxy', async ({
      page,
      request,
      baseURL,
    }) => {
      const headers = {'X-Requested-With': 'XMLHttpRequest'};
      const namespace = process.env.QUAY_HOSTED_NAMESPACE;
      const userResponse = await request.get('/api/v1/user/', {headers});
      expect(userResponse.status()).toBe(200);
      const user = await userResponse.json();
      const prefix =
        namespace === user.username
          ? '/api/v1/user'
          : `/api/v1/organization/${encodeURIComponent(namespace)}`;
      const catalogResponse = await request.get('/api/v1/plans/', {headers});
      expect(catalogResponse.status()).toBe(200);
      const {plans}: {plans: Plan[]} = await catalogResponse.json();
      const subscriptionResponse = await request.get(`${prefix}/plan`, {
        headers,
      });
      expect(subscriptionResponse.status()).toBe(200);
      const subscription = await subscriptionResponse.json();
      const available = plans.filter(
        (plan) =>
          !plan.deprecated &&
          !plan.plans_page_hidden &&
          plan.stripeId !== subscription.plan &&
          (namespace === user.username ||
            plan.stripeId === 'free' ||
            plan.bus_features),
      );
      const apiRequests: {
        url: string;
        method: string;
        authorization?: string;
      }[] = [];
      page.on('request', (req) => {
        if (new URL(req.url()).pathname.startsWith('/api/v1/')) {
          apiRequests.push({
            url: req.url(),
            method: req.method(),
            authorization: req.headers().authorization,
          });
        }
      });
      await page.goto(`/organization/${encodeURIComponent(namespace)}/plans`);
      await expect(
        page.getByRole('heading', {name: 'Choose a plan', exact: true}),
      ).toBeVisible();
      await expect(page.getByTestId('current-plan-card')).toBeVisible();
      await expect(page.getByTestId(/^available-plan-/)).toHaveCount(
        available.length,
      );
      // Reviewing an existing paid plan change must not create a second Checkout session.
      const paidAlternative = available.find((plan) => plan.price > 0);
      if (subscription.hasSubscription && paidAlternative) {
        await page
          .getByRole('button', {
            name: `Select ${paidAlternative.title}`,
            exact: true,
          })
          .click();
        const dialog = page.getByRole('dialog');
        await expect(dialog).toContainText('Confirm plan change');
        await dialog.getByRole('button', {name: 'Cancel', exact: true}).click();
        await expect(dialog).not.toBeVisible();
      }
      await page
        .getByRole('link', {name: 'Plan information', exact: true})
        .click();
      await expect(page.getByTestId('plan-information')).toBeVisible();
      await expect(page.getByTestId('invoice-summary')).toHaveText(
        /^\d+ invoices?$/,
      );
      expect(apiRequests.length).toBeGreaterThan(0);
      for (const req of apiRequests) {
        expect(new URL(req.url).origin).toBe(new URL(baseURL).origin);
        expect(req.authorization).toBeUndefined();
        expect(['GET', 'HEAD']).toContain(req.method);
      }
    });
  },
);
