import {
  formatPlanPrice,
  formatInvoiceDate,
  filterInvoices,
  getAvailablePlans,
  getPlanInformationPath,
  getCardSetupReturnUrls,
  summarizeSampleCard,
} from './billing';
import type {Plan} from 'src/resources/BillingResource';
import invoices from 'src/tests/fake-db/data/billing/invoices.json';

const now = new Date(2026, 9, 12);
const details = {
  owner: ' Jane Smith ',
  number: '4242 4242 4242 4242',
  expiry: '12/29',
  securityCode: '123',
};

describe('billing helpers', () => {
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
