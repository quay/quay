import {
  formatPlanPrice,
  formatInvoiceDate,
  filterInvoices,
  getAvailablePlans,
  getPlanInformationPath,
  getCardSetupReturnUrls,
  getPlanCheckoutReturnUrls,
  getPlanChangeAction,
  getStripeCheckoutUrl,
  getBillingErrorMessage,
  summarizeSampleCard,
} from './billing';
import {AxiosError} from 'axios';
import type {Plan, Subscription} from 'src/resources/BillingResource';
import invoices from 'src/tests/fake-db/data/billing/invoices.json';

const now = new Date(2026, 9, 12);
const details = {
  owner: ' Jane Smith ',
  number: '4242 4242 4242 4242',
  expiry: '12/29',
  securityCode: '123',
};

describe('billing helpers', () => {
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
  it('uses checkout only for new paid subscriptions outside the prototype', () => {
    const subscriber = {
      hasSubscription: true,
      plan: 'existing',
    } as Subscription;
    const newCustomer = {hasSubscription: false, plan: 'free'} as Subscription;
    const paid = {price: 3000} as Plan;
    const free = {price: 0} as Plan;
    expect(getPlanChangeAction(subscriber, paid, false)).toBe('update');
    expect(getPlanChangeAction(subscriber, free, false)).toBe('update');
    expect(getPlanChangeAction(newCustomer, paid, false)).toBe('checkout');
    expect(
      getPlanChangeAction(
        {...newCustomer, isExistingCustomer: true},
        paid,
        false,
      ),
    ).toBe('checkout');
    expect(getPlanChangeAction(subscriber, paid, true)).toBe('checkout');
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

  it('returns only masked card summary fields', () => {
    expect(summarizeSampleCard(details, now)).toEqual({
      card: {
        owner: 'Jane Smith',
        type: 'Visa',
        last4: '4242',
        exp_month: 12,
        exp_year: 2029,
      },
      error: null,
    });
  });

  it.each([
    [{owner: ''}, 'Enter the cardholder name.'],
    [{number: '4242 4242 4242 4241'}, 'Enter a valid sample card number.'],
    [{number: '4242'}, 'Enter a valid sample card number.'],
    [{expiry: '09/26'}, 'Enter a valid expiration date in MM/YY format.'],
    [{expiry: '13/29'}, 'Enter a valid expiration date in MM/YY format.'],
    [{expiry: 'invalid'}, 'Enter a valid expiration date in MM/YY format.'],
    [{securityCode: '12'}, 'Enter a 3-digit security code.'],
  ])('rejects invalid or expired details (%j)', (override, error) => {
    expect(summarizeSampleCard({...details, ...override}, now)).toEqual({
      card: null,
      error,
    });
  });

  it('accepts a card through its expiration month', () => {
    expect(
      summarizeSampleCard({...details, expiry: '10/26'}, now).error,
    ).toBeNull();
  });

  it('recognizes Mastercard and American Express, including Amex security codes', () => {
    expect(
      summarizeSampleCard({...details, number: '5555555555554444'}, now).card
        ?.type,
    ).toBe('Mastercard');
    expect(
      summarizeSampleCard(
        {...details, number: '378282246310005', securityCode: '1234'},
        now,
      ).card?.type,
    ).toBe('American Express');
    expect(
      summarizeSampleCard({...details, number: '378282246310005'}, now).card,
    ).toBeNull();
  });
});
