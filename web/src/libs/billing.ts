import type {
  BillingCard,
  Invoice,
  Plan,
  Subscription,
} from 'src/resources/BillingResource';
import {isAxiosError} from 'axios';
import {getErrorMessageFromUnknown} from 'src/resources/ErrorHandling';

export function getPlanInformationPath(namespace: string): string {
  return `/organization/${encodeURIComponent(
    namespace,
  )}?tab=Settings&settingsTab=billinginformation`;
}

export function getPlanApiPath(organization: string | null = null): string {
  return organization === null
    ? '/api/v1/user/plan'
    : `/api/v1/organization/${encodeURIComponent(organization)}/plan`;
}

export function getPlanChangeReturnPath(
  namespace: string,
  plan: string,
): string {
  const params = new URLSearchParams({
    planChange: 'returned',
    checkoutPlan: plan,
  });
  return `${getPlanInformationPath(namespace)}&${params}`;
}

export function isPlanChangeConfirmed(
  subscription: Subscription | null | undefined,
  expectedPlan: string | null,
): boolean {
  if (!expectedPlan || !subscription || subscription.plan !== expectedPlan) {
    return false;
  }
  if (expectedPlan === 'free') return subscription.hasSubscription === false;

  // Older Quay deployments omit status; still require a subscribed account.
  return (
    subscription.hasSubscription === true &&
    (subscription.status == null ||
      subscription.status === 'active' ||
      subscription.status === 'trialing')
  );
}

export function getCardSetupReturnUrls(
  namespace: string,
  origin: string,
): {success_url: string; cancel_url: string} {
  const url = new URL(getPlanInformationPath(namespace), origin);
  url.searchParams.set('paymentMethod', 'returned');
  const success_url = url.toString();
  url.searchParams.set('paymentMethod', 'canceled');
  return {success_url, cancel_url: url.toString()};
}

export function getPlanCheckoutReturnUrls(
  namespace: string,
  origin: string,
  plan: string,
): {success_url: string; cancel_url: string} {
  const url = new URL(getPlanInformationPath(namespace), origin);
  url.searchParams.set('planCheckout', 'returned');
  url.searchParams.set('checkoutPlan', plan);
  const success_url = url.toString();
  url.searchParams.set('planCheckout', 'canceled');
  return {success_url, cancel_url: url.toString()};
}

export function getPlanChangeAction(
  current: Subscription,
  plan: Plan,
  isPrototype: boolean,
): 'checkout' | 'update' {
  // Creating checkout for a subscriber can create a second Stripe subscription.
  return plan.price > 0 && (isPrototype || !current.hasSubscription)
    ? 'checkout'
    : 'update';
}

export function getStripeCheckoutUrl(
  value: string,
  origin: string,
  fake = false,
): string {
  const url = new URL(value, origin);
  const isStripe = url.origin === 'https://checkout.stripe.com';
  const isPreview =
    process.env.MOCK_API === 'true' &&
    url.origin === origin &&
    url.searchParams.get('prototypeCheckout') === '1';
  const isLocalFake =
    fake &&
    url.origin === origin &&
    ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname) &&
    url.pathname === '/fake-checkout' &&
    !!url.searchParams.get('session');
  if (
    (!isStripe && !isPreview && !isLocalFake) ||
    url.username ||
    url.password
  ) {
    throw new Error('Quay did not return a valid Stripe Checkout URL.');
  }
  return url.toString();
}

export function getBillingErrorMessage(error: unknown): string {
  if (
    isAxiosError<{carderror?: string}>(error) &&
    error.response?.status === 402
  ) {
    return 'Your payment could not be completed. Update your payment method and try again.';
  }
  return getErrorMessageFromUnknown(error);
}

export function formatPlanPrice(price: number): string {
  return price === 0 ? 'Free' : `$${(price / 100).toFixed(2)}/month`;
}

export function formatInvoiceDate(timestamp: number, locale?: string): string {
  return new Date(timestamp * 1000).toLocaleDateString(locale, {
    timeZone: 'UTC',
  });
}

export function filterInvoices(
  invoices: Invoice[],
  query: string,
  locale?: string,
): Invoice[] {
  const terms = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  if (!terms.length) return invoices;
  return invoices.filter((invoice) => {
    const dates = [
      invoice.date,
      invoice.period_start,
      invoice.period_end,
    ].flatMap((timestamp) => [
      formatInvoiceDate(timestamp, locale),
      new Date(timestamp * 1000).toISOString().slice(0, 10),
      new Date(timestamp * 1000).toLocaleDateString(locale, {
        timeZone: 'UTC',
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      }),
    ]);
    const keywords = [
      invoice.id,
      invoice.plan ?? '',
      (invoice.total / 100).toFixed(2),
      `$${(invoice.total / 100).toFixed(2)}`,
      ...dates,
    ]
      .join(' ')
      .toLocaleLowerCase();
    return terms.every((term) =>
      term === 'paid'
        ? invoice.paid
        : term === 'unpaid'
        ? !invoice.paid
        : keywords.includes(term),
    );
  });
}

export function getAvailablePlans(
  plans: Plan[],
  current: string,
  isOrg: boolean,
): Plan[] {
  return plans.filter(
    (plan) =>
      plan.stripeId !== current &&
      !plan.deprecated &&
      !plan.plans_page_hidden &&
      (!isOrg || plan.bus_features || plan.price === 0),
  );
}

export function getOrganizationCreationPlans(plans: Plan[]): Plan[] {
  return plans
    .filter(
      (plan) =>
        !plan.deprecated &&
        !plan.plans_page_hidden &&
        (plan.stripeId === 'free' || plan.bus_features),
    )
    .sort((left, right) => left.price - right.price);
}

export type SampleCardDetails = {
  owner: string;
  number: string;
  expiry: string;
  securityCode: string;
};

// Convert the temporary form values into a masked card summary.
export function summarizeSampleCard(
  details: SampleCardDetails,
  now = new Date(),
): {card: BillingCard | null; error: string | null} {
  const number = details.number.replace(/[\s-]/g, '');
  if (!details.owner.trim()) {
    return {card: null, error: 'Enter the cardholder name.'};
  }
  if (!/^\d{13,19}$/.test(number)) {
    return {card: null, error: 'Enter a valid sample card number.'};
  }
  const digits = number.split('').reverse().map(Number);
  const checksum = digits.reduce((sum, digit, index) => {
    const value = index % 2 === 0 ? digit : digit * 2;
    return sum + (value > 9 ? value - 9 : value);
  }, 0);
  if (checksum % 10 !== 0) {
    return {card: null, error: 'Enter a valid sample card number.'};
  }
  const expiry = details.expiry.match(/^(\d{2})\s*\/\s*(\d{2}|\d{4})$/);
  const month = expiry ? Number(expiry[1]) : 0;
  const year = expiry
    ? Number(expiry[2]) + (expiry[2].length === 2 ? 2000 : 0)
    : 0;
  if (
    month < 1 ||
    month > 12 ||
    year < now.getFullYear() ||
    (year === now.getFullYear() && month < now.getMonth() + 1)
  ) {
    return {
      card: null,
      error: 'Enter a valid expiration date in MM/YY format.',
    };
  }
  const isAmex = /^3[47]/.test(number);
  if (!(isAmex ? /^\d{4}$/ : /^\d{3}$/).test(details.securityCode)) {
    return {
      card: null,
      error: `Enter a ${isAmex ? 4 : 3}-digit security code.`,
    };
  }
  return {
    card: {
      owner: details.owner.trim(),
      type: isAmex
        ? 'American Express'
        : /^[25]/.test(number)
        ? 'Mastercard'
        : 'Visa',
      last4: number.slice(-4),
      exp_month: month,
      exp_year: year,
    },
    error: null,
  };
}
