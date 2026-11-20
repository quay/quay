import {test, expect} from '../../fixtures/isolated-account';
import type {Plan} from '../../../src/resources/BillingResource';

test.describe(
  'FakeStripe checkout API',
  {tag: ['@billing', '@feature:BILLING']},
  () => {
    test.skip(
      process.env.PLAYWRIGHT_FAKE_CHECKOUT !== 'true',
      'Requires the local FakeStripe provider.',
    );

    for (const organization of [false, true]) {
      test(`${
        organization ? 'organization' : 'personal'
      } checkout remains free until completion and persists plan changes`, async ({
        billingAccount,
        api,
        baseURL,
        playwright,
      }) => {
        const request = billingAccount.context.request;
        const owner = organization ? await api.organization('fakepay') : null;
        const namespace = owner?.name ?? billingAccount.username;
        const base = organization
          ? `/api/v1/organization/${namespace}`
          : '/api/v1/user';
        const {plans}: {plans: Plan[]} = await (
          await request.get('/api/v1/plans/')
        ).json();
        const paid = plans.filter(
          (plan) =>
            plan.price > 0 &&
            !plan.deprecated &&
            !plan.plans_page_hidden &&
            (!organization || plan.bus_features),
        );
        expect(paid.length).toBeGreaterThan(1);
        const csrf = {'X-CSRF-Token': await billingAccount.client.getToken()};
        const returnUrl = `${baseURL}/organization/${namespace}?tab=Settings&settingsTab=billinginformation`;
        const result = await request.post(`${base}/plan`, {
          headers: csrf,
          data: {
            plan: paid[0].stripeId,
            success_url: `${returnUrl}&planCheckout=returned`,
            cancel_url: `${returnUrl}&planCheckout=canceled`,
          },
        });
        expect(result.status()).toBe(200);
        const session = await result.json();
        expect(session.fake).toBe(true);
        expect(
          (
            await request.post(`${base}/plan`, {
              headers: csrf,
              data: {
                plan: paid[0].stripeId,
                success_url: 'https://quay.io/return',
                cancel_url: 'https://quay.io/cancel',
              },
            })
          ).status(),
        ).toBe(400);
        const url = new URL(session.url);
        expect(url.origin).toBe(new URL(baseURL).origin);
        expect(url.pathname).toBe('/fake-checkout');
        const path = `${base}/checkout/${encodeURIComponent(
          url.searchParams.get('session'),
        )}`;
        expect((await request.get(path)).status()).toBe(200);
        expect((await request.get(`${path}tampered`)).status()).toBe(400);
        const anonymous = await playwright.request.newContext({baseURL});
        try {
          expect((await anonymous.get(path)).status()).toBe(401);
        } finally {
          await anonymous.dispose();
        }
        const other = await api.organization('other');
        expect(
          (
            await request.get(
              `/api/v1/organization/${other.name}/checkout/${encodeURIComponent(
                url.searchParams.get('session'),
              )}`,
            )
          ).status(),
        ).toBe(404);
        expect(
          (await (await request.get(`${base}/plan`)).json()).hasSubscription,
        ).toBe(false);
        expect((await request.post(path)).status()).toBeGreaterThanOrEqual(400);
        expect((await request.post(path, {headers: csrf})).status()).toBe(200);
        expect((await request.post(path, {headers: csrf})).status()).toBe(200);
        for (let read = 0; read < 3; read++) {
          const subscription = await (await request.get(`${base}/plan`)).json();
          expect(subscription.hasSubscription).toBe(true);
          expect(subscription.plan).toBe(paid[0].stripeId);
        }
        const cardSetup = await request.post(`${base}/card`, {
          headers: csrf,
          data: {
            success_url: `${returnUrl}&paymentMethod=returned`,
            cancel_url: `${returnUrl}&paymentMethod=canceled`,
          },
        });
        expect(cardSetup.status()).toBe(200);
        const cardSession = new URL(
          (await cardSetup.json()).url,
        ).searchParams.get('session');
        const cardPath = `${base}/checkout/${encodeURIComponent(cardSession)}`;
        expect((await (await request.get(cardPath)).json()).mode).toBe('setup');
        expect((await request.post(cardPath, {headers: csrf})).status()).toBe(
          200,
        );
        expect(
          (await (await request.get(`${base}/card`)).json()).card.last4,
        ).toBe('4242');
        expect(
          (
            await request.put(`${base}/plan`, {
              headers: csrf,
              data: {plan: paid[1].stripeId},
            })
          ).status(),
        ).toBe(200);
        expect((await (await request.get(`${base}/plan`)).json()).plan).toBe(
          paid[1].stripeId,
        );
        // Replaying a completed Checkout must not undo a later plan change.
        expect((await request.post(path, {headers: csrf})).status()).toBe(200);
        expect((await (await request.get(`${base}/plan`)).json()).plan).toBe(
          paid[1].stripeId,
        );
        expect(
          (
            await request.put(`${base}/plan`, {
              headers: csrf,
              data: {plan: 'free'},
            })
          ).status(),
        ).toBe(200);
        expect(
          (await (await request.get(`${base}/plan`)).json()).hasSubscription,
        ).toBe(false);
      });
    }
  },
);
