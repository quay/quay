import {test, expect} from '@playwright/test';
import type {Plan, Subscription} from '../../../src/resources/BillingResource';

const namespace = process.env.QUAY_BILLING_NAMESPACE;

test.describe(
  'Quay.io session billing',
  {tag: ['@billing', '@feature:BILLING']},
  () => {
    test.skip(
      !namespace || !process.env.QUAY_BILLING_STORAGE_STATE,
      'Requires a designated namespace and an authenticated session for the deployment under test.',
    );

    test('reads native billing and reviews an existing plan change without submitting it', async ({
      page,
      request,
      baseURL,
    }) => {
      const userResponse = await request.get('/api/v1/user/');
      expect(userResponse.status()).toBe(200);
      const user = await userResponse.json();
      const prefix =
        namespace === user.username
          ? '/api/v1/user'
          : `/api/v1/organization/${encodeURIComponent(namespace)}`;
      const subscriptionResponse = await request.get(`${prefix}/plan`);
      expect(subscriptionResponse.status()).toBe(200);
      const subscription: Subscription = await subscriptionResponse.json();
      const catalogResponse = await request.get('/api/v1/plans/');
      expect(catalogResponse.status()).toBe(200);
      const {plans}: {plans: Plan[]} = await catalogResponse.json();
      const available = plans.filter(
        (plan) =>
          !plan.deprecated &&
          !plan.plans_page_hidden &&
          plan.stripeId !== subscription.plan &&
          (namespace === user.username ||
            plan.bus_features ||
            plan.stripeId === 'free'),
      );
      const mutations: string[] = [];
      const apiRequests: {origin: string; bearer: boolean}[] = [];
      page.on('request', (request) => {
        const url = new URL(request.url());
        if (!url.pathname.startsWith('/api/v1/')) return;
        apiRequests.push({
          origin: url.origin,
          bearer: !!request.headers().authorization,
        });
        if (!['GET', 'HEAD'].includes(request.method()))
          mutations.push(request.method());
      });
      await page.goto(`/organization/${encodeURIComponent(namespace)}/plans`);
      await expect(page.getByTestId(/^available-plan-/)).toHaveCount(
        available.length,
      );
      if (subscription.hasSubscription && available.length) {
        await page
          .getByRole('button', {
            name: `Select ${available[0].title}`,
            exact: true,
          })
          .click();
        const dialog = page.getByRole('dialog');
        await expect(dialog).toContainText('Confirm plan change');
        await dialog.getByRole('button', {name: 'Cancel', exact: true}).click();
        await expect(dialog).not.toBeVisible();
      }
      expect(mutations).toEqual([]);
      expect(apiRequests.length).toBeGreaterThan(0);
      for (const request of apiRequests) {
        expect(request.origin).toBe(new URL(baseURL).origin);
        expect(request.bearer).toBe(false);
      }
    });

    test('opens real Stripe Checkout for a selected new subscription and returns without payment', async ({
      page,
      request,
      baseURL,
    }) => {
      test.skip(
        process.env.QUAY_BILLING_CREATE_CHECKOUT !== 'true' ||
          !process.env.QUAY_BILLING_CHECKOUT_PLAN,
        'Session creation requires explicit opt-in and a selected paid plan.',
      );
      const userResponse = await request.get('/api/v1/user/');
      expect(userResponse.status()).toBe(200);
      const user = await userResponse.json();
      const prefix =
        namespace === user.username
          ? '/api/v1/user'
          : `/api/v1/organization/${encodeURIComponent(namespace)}`;
      const subscriptionResponse = await request.get(`${prefix}/plan`);
      expect(subscriptionResponse.status()).toBe(200);
      const subscription: Subscription = await subscriptionResponse.json();
      expect(subscription.hasSubscription).toBe(false);
      const catalogResponse = await request.get('/api/v1/plans/');
      expect(catalogResponse.status()).toBe(200);
      const {plans}: {plans: Plan[]} = await catalogResponse.json();
      const plan = plans.find(
        (entry) =>
          entry.stripeId === process.env.QUAY_BILLING_CHECKOUT_PLAN &&
          entry.price > 0 &&
          !entry.deprecated &&
          !entry.plans_page_hidden &&
          (namespace === user.username || entry.bus_features),
      );
      expect(plan).toBeDefined();
      await page.goto(`/organization/${encodeURIComponent(namespace)}/plans`);
      const checkoutResponse = page.waitForResponse(
        (response) =>
          new URL(response.url()).pathname === `${prefix}/plan` &&
          response.request().method() === 'POST',
      );
      await page
        .getByRole('button', {name: `Select ${plan.title}`, exact: true})
        .click();
      const response = await checkoutResponse;
      expect(response.status()).toBe(200);
      const checkoutRequest = response.request();
      expect(!!checkoutRequest.headers()['x-csrf-token']).toBe(true);
      expect(!!checkoutRequest.headers().authorization).toBe(false);
      const body = checkoutRequest.postDataJSON();
      expect(body.plan).toBe(plan.stripeId);
      for (const field of ['success_url', 'cancel_url']) {
        expect(new URL(body[field]).origin).toBe(new URL(baseURL).origin);
      }
      await page.waitForURL(
        (url) => url.origin === 'https://checkout.stripe.com',
        {waitUntil: 'commit'},
      );
      // Exercise the app's cancel return without submitting Stripe's payment form.
      await page.goto(body.cancel_url);
      await expect(
        page.getByRole('heading', {name: /Stripe Checkout canceled/}),
      ).toBeVisible();
      const afterResponse = await request.get(`${prefix}/plan`);
      expect(afterResponse.status()).toBe(200);
      expect((await afterResponse.json()).hasSubscription).toBe(false);
    });
  },
);
