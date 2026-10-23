import type {Invoice, Plan, Subscription} from 'src/resources/BillingResource';
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
  pathname = '',
): {success_url: string; cancel_url: string} {
  const url = getCheckoutReturnUrl(namespace, origin, pathname);
  url.searchParams.set('paymentMethod', 'returned');
  const success_url = url.toString();
  url.searchParams.set('paymentMethod', 'canceled');
  return {success_url, cancel_url: url.toString()};
}

export function getPlanCheckoutReturnUrls(
  namespace: string,
  origin: string,
  plan: string,
  pathname = '',
): {success_url: string; cancel_url: string} {
  const url = getCheckoutReturnUrl(namespace, origin, pathname);
  url.searchParams.set('planCheckout', 'returned');
  url.searchParams.set('checkoutPlan', plan);
  const success_url = url.toString();
  url.searchParams.set('planCheckout', 'canceled');
  return {success_url, cancel_url: url.toString()};
}

function getCheckoutReturnUrl(
  namespace: string,
  origin: string,
  pathname: string,
): URL {
  const prefix =
    pathname.match(/^(.*?)\/(?:organizations|organization)(?:\/|$)/)?.[1] ?? '';
  const url = new URL(getPlanInformationPath(namespace), origin);
  url.pathname = `${prefix}${url.pathname}`;
  return url;
}

export function getPlanChangeAction(
  current: Subscription,
  plan: Plan,
): 'checkout' | 'update' {
  // Creating checkout for a subscriber can create a second Stripe subscription.
  return plan.price > 0 && !current.hasSubscription ? 'checkout' : 'update';
}

export function getStripeCheckoutUrl(
  value: string,
  origin: string,
  fake = false,
): string {
  const url = new URL(value, origin);
  const isStripe = url.origin === 'https://checkout.stripe.com';
  const isLocalFake =
    fake &&
    url.origin === origin &&
    ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname) &&
    url.pathname === '/fake-checkout' &&
    !!url.searchParams.get('session');
  if ((!isStripe && !isLocalFake) || url.username || url.password) {
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

export function getPrivateRepositoryUsage(used: number, allowance: number) {
  const isUnlimited = allowance >= Number.MAX_SAFE_INTEGER;
  return {
    isUnlimited,
    isOverLimit: !isUnlimited && used > allowance,
    value:
      isUnlimited || allowance <= 0
        ? 0
        : Math.max(0, Math.min(100, (used / allowance) * 100)),
    label: `${used} of ${isUnlimited ? 'unlimited' : allowance} private repositories used`,
  };
}
