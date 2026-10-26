import {
  formatPlanPrice,
  formatInvoiceDate,
  filterInvoices,
  getAvailablePlans,
  getOrganizationCreationPlans,
  getPrivateRepositoryUsage,
  getPlanInformationPath,
  getCardSetupReturnUrls,
  getPlanCheckoutReturnUrls,
  getPlanChangeAction,
  getStripeCheckoutUrl,
  getBillingErrorMessage,
  getPlanApiPath,
  getPlanChangeReturnPath,
  isPlanChangeConfirmed,
} from './billing';
import {AxiosError} from 'axios';
import type {Plan, Subscription} from 'src/resources/BillingResource';
import invoices from 'src/tests/fake-db/data/billing/invoices.json';

describe('billing helpers', () => {
  it('keeps checkout returns on the current origin for a double-slash router prefix', () => {
    const urls = getPlanCheckoutReturnUrls(
      'example',
      'https://quay.io',
      'bus-micro-2018',
      '//outside.invalid/organizations/new',
    );
    expect(new URL(urls.success_url).origin).toBe('https://quay.io');
    expect(new URL(urls.cancel_url).origin).toBe('https://quay.io');
  });
  it.each([
    [5, 10, 50, false, false, '5 of 10'],
    [15, 10, 100, false, true, '15 of 10'],
    [0, 0, 0, false, false, '0 of 0'],
    [1, 0, 0, false, true, '1 of 0'],
    [15, Number.MAX_SAFE_INTEGER, 0, true, false, '15 of unlimited'],
  ])(
    'bounds repository usage for %i used of %i allowed',
    (used, allowance, value, isUnlimited, isOverLimit, text) => {
      expect(getPrivateRepositoryUsage(used, allowance)).toEqual({
        value,
        isUnlimited,
        isOverLimit,
        label: `${text} private repositories used`,
      });
    },
  );
  it.each(['/settings/quay', '/beta/settings/quay', ''])(
    'preserves the checkout router base %s',
    (prefix) => {
      const pathname = `${prefix}/organizations/new`;
      const urls = getPlanCheckoutReturnUrls(
        'example',
        'https://stage.quay.io',
        'bus-micro-2018',
        pathname,
      );
      expect(new URL(urls.success_url).pathname).toBe(
        `${prefix}/organization/example`,
      );
      expect(new URL(urls.cancel_url).pathname).toBe(
        `${prefix}/organization/example`,
      );
      expect(
        new URL(
          getCardSetupReturnUrls(
            'example',
            'https://stage.quay.io',
            `${prefix}/organization/example`,
          ).success_url,
        ).pathname,
      ).toBe(`${prefix}/organization/example`);
    },
  );
  it('accepts an explicitly simulated checkout only on the same local origin', () => {
    const url = 'http://localhost:9010/fake-checkout?session=signed-session';
    expect(getStripeCheckoutUrl(url, 'http://localhost:9010', true)).toBe(url);
    expect(() => getStripeCheckoutUrl(url, 'http://localhost:9010')).toThrow();
    expect(() =>
      getStripeCheckoutUrl(url, 'http://localhost:9011', true),
    ).toThrow();
    expect(() =>
      getStripeCheckoutUrl(
        'https://quay.io/fake-checkout?session=example',
        'https://quay.io',
        true,
      ),
    ).toThrow();
    expect(() =>
      getStripeCheckoutUrl(
        '/other?session=example',
        'http://localhost:9010',
        true,
      ),
    ).toThrow();
  });
  it('offers only current organization plans, including free, ordered by price', () => {
    const catalog = [
      {stripeId: 'large', price: 6000, bus_features: true},
      {stripeId: 'personal', price: 1000, bus_features: false},
      {stripeId: 'free', price: 0, bus_features: false},
      {
        stripeId: 'hidden',
        price: 1000,
        bus_features: true,
        plans_page_hidden: true,
      },
      {stripeId: 'old', price: 1000, bus_features: true, deprecated: true},
      {stripeId: 'small', price: 3000, bus_features: true},
    ] as Plan[];
    expect(
      getOrganizationCreationPlans(catalog).map((plan) => plan.stripeId),
    ).toEqual(['free', 'small', 'large']);
    expect(catalog[0].stripeId).toBe('large');
    expect(getOrganizationCreationPlans([])).toEqual([]);
  });
  it('uses native billing endpoints for personal and organization subscriptions', () => {
    expect(getPlanApiPath()).toBe('/api/v1/user/plan');
    expect(getPlanApiPath(null)).toBe('/api/v1/user/plan');
    expect(getPlanApiPath('my-org')).toBe('/api/v1/organization/my-org/plan');
    expect(getPlanApiPath('org/name?other=1')).toBe(
      '/api/v1/organization/org%2Fname%3Fother%3D1/plan',
    );
  });

  it('verifies an existing subscription update on the billing page', () => {
    const url = new URL(
      getPlanChangeReturnPath('my-org', 'bus-micro-2018'),
      'https://quay.io',
    );
    expect(url.pathname).toBe('/organization/my-org');
    expect(url.searchParams.get('settingsTab')).toBe('billinginformation');
    expect(url.searchParams.get('planChange')).toBe('returned');
    expect(url.searchParams.get('checkoutPlan')).toBe('bus-micro-2018');
  });

  it.each([
    'https://quay.io',
    'https://stage.quay.io',
    'http://localhost:9010',
  ])('returns Checkout to its runtime origin: %s', (origin) => {
    const urls = getPlanCheckoutReturnUrls('my-org', origin, 'bus-micro-2018');
    expect(new URL(urls.success_url).origin).toBe(origin);
    expect(new URL(urls.cancel_url).origin).toBe(origin);
  });

  it.each(['active', 'trialing', null, undefined])(
    'confirms an authoritative paid subscription with status %s',
    (status) => {
      const subscription = {
        plan: 'bus-micro-2018',
        hasSubscription: true,
        status,
      } as Subscription;
      expect(isPlanChangeConfirmed(subscription, 'bus-micro-2018')).toBe(true);
    },
  );

  it.each([
    'incomplete',
    'past_due',
    'canceled',
    'unpaid',
    'incomplete_expired',
  ])('does not confirm a matching plan with payment status %s', (status) => {
    const subscription = {
      plan: 'bus-micro-2018',
      hasSubscription: true,
      status,
    } as Subscription;
    expect(isPlanChangeConfirmed(subscription, 'bus-micro-2018')).toBe(false);
  });

  it('requires backend subscription data rather than trusting the return URL', () => {
    const subscription = {
      plan: 'bus-micro-2018',
      hasSubscription: false,
      status: null,
    } as Subscription;
    expect(isPlanChangeConfirmed(null, 'bus-micro-2018')).toBe(false);
    expect(isPlanChangeConfirmed(subscription, null)).toBe(false);
    expect(isPlanChangeConfirmed(subscription, 'bus-small-2018')).toBe(false);
    expect(isPlanChangeConfirmed(subscription, 'bus-micro-2018')).toBe(false);
    expect(isPlanChangeConfirmed({...subscription, plan: 'free'}, 'free')).toBe(
      true,
    );
    expect(
      isPlanChangeConfirmed(
        {...subscription, plan: 'free', hasSubscription: true},
        'free',
      ),
    ).toBe(false);
  });

  it('explains payment failures without retrying a subscription creation', () => {
    const error = new AxiosError('Payment required');
    error.response = {
      status: 402,
      data: {carderror: 'Declined'},
    } as AxiosError['response'];
    expect(getBillingErrorMessage(error)).toContain(
      'Update your payment method',
    );
    expect(getBillingErrorMessage(new Error('No checkout URL'))).toBe(
      'No checkout URL',
    );
  });
  it('uses checkout only for new paid subscriptions ', () => {
    const subscriber = {
      hasSubscription: true,
      plan: 'existing',
    } as Subscription;
    const newCustomer = {hasSubscription: false, plan: 'free'} as Subscription;
    const paid = {price: 3000} as Plan;
    const free = {price: 0} as Plan;
    expect(getPlanChangeAction(subscriber, paid)).toBe('update');
    expect(getPlanChangeAction(subscriber, free)).toBe('update');
    expect(getPlanChangeAction(newCustomer, paid)).toBe('checkout');
    expect(
      getPlanChangeAction({...newCustomer, isExistingCustomer: true}, paid),
    ).toBe('checkout');
  });

  it('returns subscription checkout outcomes to the selected namespace with the expected plan', () => {
    const urls = getPlanCheckoutReturnUrls(
      'my-org',
      'https://localhost:9010',
      'bus-micro-2018',
    );
    const success = new URL(urls.success_url);
    const cancel = new URL(urls.cancel_url);
    expect(success.pathname).toBe('/organization/my-org');
    expect(success.searchParams.get('planCheckout')).toBe('returned');
    expect(success.searchParams.get('checkoutPlan')).toBe('bus-micro-2018');
    expect(success.searchParams.get('settingsTab')).toBe('billinginformation');
    expect(success.searchParams.has('paymentMethod')).toBe(false);
    expect(cancel.searchParams.get('planCheckout')).toBe('canceled');
  });

  it('accepts hosted Stripe Checkout and rejects unrelated or unsafe redirect URLs', () => {
    expect(
      getStripeCheckoutUrl(
        'https://checkout.stripe.com/c/pay/cs_live_example',
        'https://localhost:9010',
      ),
    ).toBe('https://checkout.stripe.com/c/pay/cs_live_example');
    for (const url of [
      'javascript:alert(1)',
      'https://example.com',
      'https://checkout.stripe.com.attacker.example',
      'http://checkout.stripe.com',
      'https://user@checkout.stripe.com',
    ]) {
      expect(() =>
        getStripeCheckoutUrl(url, 'https://localhost:9010'),
      ).toThrow();
    }
  });

  it('matches invoice keywords across dates, IDs, prices, plans, and payment status', () => {
    const matchingIds = (query: string) =>
      filterInvoices(invoices, query, 'en-US').map((invoice) => invoice.id);
    expect(matchingIds(' INV_2 ')).toEqual(['inv_2']);
    expect(matchingIds('PAID')).toEqual(['inv_1', 'inv_2']);
    expect(matchingIds('unpaid')).toEqual(['inv_3']);
    expect(matchingIds('paid inv_1')).toEqual(['inv_1']);
    expect(matchingIds('$125.00 Medium')).toEqual(['inv_1', 'inv_2', 'inv_3']);
    expect(matchingIds('September 2026')).toEqual(['inv_1']);
    expect(matchingIds('2026-07-12')).toEqual(['inv_2', 'inv_3']);
    expect(matchingIds('not-found')).toEqual([]);
    expect(filterInvoices(invoices, '   ')).toBe(invoices);
  });
  it('returns both Stripe checkout outcomes to the same namespace and Plan information tab', () => {
    expect(
      getCardSetupReturnUrls('projectquay', 'http://localhost:9010'),
    ).toEqual({
      success_url:
        'http://localhost:9010/organization/projectquay?tab=Settings&settingsTab=billinginformation&paymentMethod=returned',
      cancel_url:
        'http://localhost:9010/organization/projectquay?tab=Settings&settingsTab=billinginformation&paymentMethod=canceled',
    });
  });
  it('keeps the invoice date consistent with its PDF regardless of the browser time zone', () => {
    expect(
      formatInvoiceDate(Date.parse('2026-09-12T00:00:00Z') / 1000, 'en-US'),
    ).toBe('9/12/2026');
  });
  it('links directly to Plan information and encodes the namespace', () => {
    expect(getPlanInformationPath('sample org')).toBe(
      '/organization/sample%20org?tab=Settings&settingsTab=billinginformation',
    );
  });

  it('preserves cents and formats the free plan', () => {
    expect(formatPlanPrice(1599)).toBe('$15.99/month');
    expect(formatPlanPrice(0)).toBe('Free');
  });

  it('excludes current, hidden, deprecated, and ineligible organization plans', () => {
    const plan = (stripeId: string, extra: Partial<Plan> = {}): Plan => ({
      stripeId,
      title: stripeId,
      price: 1500,
      privateRepos: 5,
      audience: 'business',
      bus_features: true,
      deprecated: false,
      free_trial_days: 0,
      superseded_by: null,
      plans_page_hidden: false,
      ...extra,
    });
    const plans = [
      plan('current'),
      plan('hidden', {plans_page_hidden: true}),
      plan('old', {deprecated: true}),
      plan('personal', {bus_features: false}),
      plan('free', {price: 0, bus_features: false}),
      plan('large'),
    ];
    expect(
      getAvailablePlans(plans, 'current', true).map((entry) => entry.stripeId),
    ).toEqual(['free', 'large']);
    expect(
      getAvailablePlans(plans, 'current', false).map((entry) => entry.stripeId),
    ).toEqual(['personal', 'free', 'large']);
  });
});
