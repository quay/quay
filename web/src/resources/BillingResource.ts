import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';

export interface Subscription {
  hasSubscription: boolean;
  isExistingCustomer: boolean;
  plan: string; // TODO: should probably be an enum
  usedPrivateRepos: number;
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
  const response: AxiosResponse<PlansResponse> = await axios.get(
    '/api/v1/plans/',
  );
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
