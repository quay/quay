import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {ResourceError} from './ErrorHandling';
import {getPlanApiPath, getStripeCheckoutUrl} from 'src/libs/billing';

export type SubscriptionStatus =
  | 'active'
  | 'trialing'
  | 'past_due'
  | 'incomplete'
  | 'canceled';

export interface Subscription {
  hasSubscription: boolean;
  isExistingCustomer: boolean;
  plan: string;
  usedPrivateRepos: number;
  status: SubscriptionStatus | null;
  trialStart: number | null;
  trialEnd: number | null;
  currentPeriodEnd: number | null;
}

export async function fetchSubscription(org: string = null) {
  const response: AxiosResponse<Subscription> = await axios.get(
    getPlanApiPath(org),
  );
  return response.data;
}

export async function setSubscription(
  plan: string,
  org: string = null,
  token: string = null,
) {
  const body: {plan: string; token?: string} = {plan: plan};
  if (token != null) {
    body.token = token;
  }
  await axios.put(getPlanApiPath(org), body);
}

interface PlansResponse {
  plans: Plan[];
}

export interface Plan {
  title: string;
  price: number;
  privateRepos: number;
  stripeId: string;
  audience: string;
  bus_features: boolean;
  deprecated: boolean;
  free_trial_days: number;
  superseded_by: string;
  plans_page_hidden: boolean;
}

export async function fetchPlans() {
  const response: AxiosResponse<PlansResponse> =
    await axios.get('/api/v1/plans/');
  return response.data.plans;
}

export interface PrivateAllowed {
  privateAllowed: boolean;
  privateCount: number;
}

export async function fetchPrivateAllowed(org: string = null) {
  const url: string =
    org != null
      ? `/api/v1/organization/${org}/private`
      : '/api/v1/user/private';
  const response: AxiosResponse<PrivateAllowed> = await axios.get(url);
  return response.data;
}

export interface BillingCardResponse {
  card: BillingCard;
}

export interface BillingCard {
  owner: string;
  type: string;
  last4: string;
  exp_month: number;
  exp_year: number;
}

export async function fetchCard(org: string = null) {
  const url: string =
    org != null ? `/api/v1/organization/${org}/card` : '/api/v1/user/card';
  const response: AxiosResponse<BillingCardResponse> = await axios.get(url);
  return response.data.card;
}

export interface CardSetupReturnUrls {
  success_url: string;
  cancel_url: string;
}

export async function createCardSetupSession(
  returnUrls: CardSetupReturnUrls,
  org: string = null,
): Promise<{url: string}> {
  const path =
    org != null
      ? `/api/v1/organization/${encodeURIComponent(org)}/card`
      : '/api/v1/user/card';
  const response = await axios.post<{url: string; fake?: boolean}>(
    path,
    returnUrls,
  );
  if (!response.data?.url) {
    throw new Error('Stripe did not return a checkout URL. Please try again.');
  }
  return {
    ...response.data,
    url: getStripeCheckoutUrl(
      response.data.url,
      window.location.origin,
      response.data.fake === true,
    ),
  };
}

export async function createSubscriptionCheckoutSession(
  plan: string,
  returnUrls: CardSetupReturnUrls,
  org: string = null,
): Promise<{url: string}> {
  const response = await axios.post<{url: string; fake?: boolean}>(
    getPlanApiPath(org),
    {
      plan,
      ...returnUrls,
    },
  );
  if (!response.data?.url)
    throw new Error('Stripe did not return a checkout URL. Please try again.');
  return {
    ...response.data,
    url: getStripeCheckoutUrl(
      response.data.url,
      window.location.origin,
      response.data.fake === true,
    ),
  };
}

export interface FakeCheckoutSession {
  mode: 'subscription' | 'setup';
  plan: Plan | null;
  cancel_url: string;
  fake: true;
}

function getFakeCheckoutPath(
  session: string,
  organization: string | null,
): string {
  const base = organization
    ? `/api/v1/organization/${encodeURIComponent(organization)}`
    : '/api/v1/user';
  return `${base}/checkout/${encodeURIComponent(session)}`;
}

export async function fetchFakeCheckout(
  session: string,
  organization: string | null,
): Promise<FakeCheckoutSession> {
  return (
    await axios.get<FakeCheckoutSession>(
      getFakeCheckoutPath(session, organization),
    )
  ).data;
}

export async function completeFakeCheckout(
  session: string,
  organization: string | null,
): Promise<{url: string}> {
  return (
    await axios.post<{url: string}>(getFakeCheckoutPath(session, organization))
  ).data;
}

export interface MarketplaceSubscription {
  id: string;
  subscription_id?: string;
  sku: string;
  quantity: number;
  assigned_to_org?: string | null;
  metadata: {privateRepos: number};
}

export async function fetchMarketplaceSubscriptions(
  org: string = null,
): Promise<MarketplaceSubscription[]> {
  const url: string =
    org != null
      ? `/api/v1/organization/${org}/marketplace`
      : '/api/v1/user/marketplace';
  const response = await axios.get<MarketplaceSubscription[]>(url);
  return response.data;
}

export async function setMarketplaceOrgAttachment(
  org: string,
  subscriptions: Array<any>,
) {
  try {
    await axios.post(`/api/v1/organization/${org}/marketplace`, {
      subscriptions: subscriptions,
    });
  } catch (error) {
    throw new ResourceError(
      'Unable to bind subscriptions to org',
      `${org}`,
      error,
    );
  }
  return;
}

export async function setMarketplaceOrgRemoval(
  org: string,
  subscriptions: Array<any>,
) {
  try {
    await axios.post(`/api/v1/organization/${org}/marketplace/batchremove`, {
      subscriptions: subscriptions,
    });
  } catch (error) {
    throw new ResourceError(
      'Unable to remove subscriptions from org',
      `${org}`,
      error,
    );
  }
  return;
}

export interface Invoice {
  id: string;
  download_url?: string;
  date: number;
  period_start: number;
  period_end: number;
  paid: boolean;
  amount_due: number;
  next_payment_attempt: number | null;
  attempted: boolean;
  closed: boolean;
  total: number;
  plan: string | null;
}

export async function fetchInvoices(org: string = null) {
  const url =
    org != null
      ? `/api/v1/organization/${org}/invoices`
      : '/api/v1/user/invoices';
  const response: AxiosResponse<{invoices: Invoice[]}> = await axios.get(url);
  return response.data.invoices;
}
