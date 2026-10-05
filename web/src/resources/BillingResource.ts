import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {ResourceError} from './ErrorHandling';

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
  const url: string =
    org != null ? `/api/v1/organization/${org}/plan` : '/api/v1/user/plan';
  const response: AxiosResponse<Subscription> = await axios.get(url);
  return response.data;
}

export async function setSubscription(
  plan: string,
  org: string = null,
  token: string = null,
) {
  const url: string =
    org != null ? `/api/v1/organization/${org}/plan` : '/api/v1/user/plan';
  const body: {plan: string; token?: string} = {plan: plan};
  if (token != null) {
    body.token = token;
  }
  await axios.put(url, body);
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

export async function fetchMarketplaceSubscriptions(org: string = null) {
  const url: string =
    org != null
      ? `/api/v1/organization/${org}/marketplace`
      : '/api/v1/user/marketplace';
  const response: AxiosResponse = await axios.get(url);
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
