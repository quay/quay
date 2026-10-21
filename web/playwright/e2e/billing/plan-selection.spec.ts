import {test, expect} from '../../fixtures/isolated-account';
import type {Plan} from '../../../src/resources/BillingResource';

test.describe(
  'Native billing plan selection',
  {tag: ['@billing', '@feature:BILLING']},
  () => {
    test('loads personal plans using the signed-in session', async ({
      billingPage: page,
      billingAccount,
      baseURL,
    }) => {
      const requests: {origin: string; path: string; bearer: boolean}[] = [];
      page.on('request', (request) => {
        const url = new URL(request.url());
        if (url.pathname.endsWith('/plan')) {
          requests.push({
            origin: url.origin,
            path: url.pathname,
            bearer: !!request.headers().authorization,
          });
        }
      });
      const response = await page.request.get('/api/v1/plans/');
      expect(response.ok()).toBe(true);
      const {plans}: {plans: Plan[]} = await response.json();
      const available = plans.filter(
        (plan) =>
          !plan.deprecated &&
          !plan.plans_page_hidden &&
          plan.stripeId !== 'free',
      );
      await page.goto(`/organization/${billingAccount.username}/plans`);
      await expect(page.getByTestId(/^available-plan-/)).toHaveCount(
        available.length,
      );
      for (const plan of available) {
        await expect(
          page.getByRole('button', {name: `Select ${plan.title}`, exact: true}),
        ).toBeEnabled();
      }
      expect(requests.length).toBeGreaterThan(0);
      for (const request of requests) {
        expect(request.origin).toBe(new URL(baseURL).origin);
        expect(request.path).toBe('/api/v1/user/plan');
        expect(request.bearer).toBe(false);
      }
    });

    for (const organization of [false, true]) {
      test(`shows canceled checkout for a ${
        organization ? 'business' : 'personal'
      } namespace`, async ({billingPage: page, billingAccount, api}) => {
        const namespace = organization
          ? (await api.organization('billing')).name
          : billingAccount.username;
        const mutations: string[] = [];
        page.on('request', (request) => {
          if (
            request.method() !== 'GET' &&
            new URL(request.url()).pathname.endsWith('/plan')
          ) {
            mutations.push(request.method());
          }
        });
        const endpoint = organization
          ? `/api/v1/organization/${namespace}/plan`
          : '/api/v1/user/plan';
        const subscription = page.waitForResponse(
          (response) =>
            new URL(response.url()).pathname === endpoint &&
            response.request().method() === 'GET' &&
            response.status() === 200,
        );
        await page.goto(
          `/organization/${namespace}?tab=Settings&settingsTab=billinginformation&planCheckout=canceled`,
        );
        await subscription;
        await expect(
          page.getByRole('heading', {name: /Stripe Checkout canceled/}),
        ).toBeVisible();
        await expect(page.getByTestId('plan-change-result')).toHaveCount(0);
        expect(mutations).toEqual([]);
      });
    }

    test('does not report success for an unconfirmed plan in a return URL', async ({
      billingPage: page,
      billingAccount,
    }) => {
      await page.goto(
        `/organization/${billingAccount.username}?tab=Settings&settingsTab=billinginformation&planChange=returned&checkoutPlan=bus-micro-2018`,
      );
      const result = page.getByTestId('plan-change-result');
      await expect(result).toHaveAttribute('aria-live', 'polite');
      await expect(result).toContainText(
        'Checking your subscription with Quay',
      );
      await expect(result).toContainText(
        'Your subscription has not been confirmed yet.',
        {
          timeout: 15000,
        },
      );
      await expect(result).not.toContainText(
        'Your subscription has been updated.',
      );
    });

    test('each paid-plan button sends its own plan and reports a backend checkout error', async ({
      billingPage: page,
      billingAccount,
      baseURL,
    }) => {
      // Opt in only on a local backend without Stripe credentials.
      test.skip(
        process.env.PLAYWRIGHT_BILLING_EXPECT_CHECKOUT_ERROR !== 'true',
        'Requires an explicitly selected backend where checkout is unavailable.',
      );
      const response = await page.request.get('/api/v1/plans/');
      const {plans}: {plans: Plan[]} = await response.json();
      const paid = plans.filter(
        (plan) => !plan.deprecated && !plan.plans_page_hidden && plan.price > 0,
      );
      expect(paid.length).toBeGreaterThan(0);
      await page.goto(`/organization/${billingAccount.username}/plans`);
      for (const plan of paid) {
        const checkout = page.waitForResponse(
          (response) =>
            new URL(response.url()).pathname === '/api/v1/user/plan' &&
            response.request().method() === 'POST',
        );
        await page
          .getByRole('button', {name: `Select ${plan.title}`, exact: true})
          .click();
        const result = await checkout;
        expect(result.status()).toBeGreaterThanOrEqual(400);
        const request = result.request();
        expect(!!request.headers()['x-csrf-token']).toBe(true);
        expect(!!request.headers().authorization).toBe(false);
        const body = request.postDataJSON();
        expect(body.plan).toBe(plan.stripeId);
        for (const [field, outcome] of [
          ['success_url', 'returned'],
          ['cancel_url', 'canceled'],
        ]) {
          const url = new URL(body[field]);
          expect(url.origin).toBe(new URL(baseURL).origin);
          expect(url.pathname).toBe(`/organization/${billingAccount.username}`);
          expect(url.searchParams.get('planCheckout')).toBe(outcome);
          expect(url.searchParams.get('checkoutPlan')).toBe(plan.stripeId);
        }
        await expect(
          page.getByRole('heading', {name: /Unable to open plan checkout/}),
        ).toBeVisible();
        await expect(
          page.getByRole('button', {name: `Select ${plan.title}`, exact: true}),
        ).toBeEnabled();
        await expect(page).toHaveURL(/\/plans$/);
      }
    });
  },
);
