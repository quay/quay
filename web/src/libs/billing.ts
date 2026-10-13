import type {BillingCard, Invoice, Plan} from 'src/resources/BillingResource';

export function getPlanInformationPath(namespace: string): string {
  return `/organization/${encodeURIComponent(
    namespace,
  )}?tab=Settings&settingsTab=billinginformation`;
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
