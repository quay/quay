import {mock} from '../../MockAxios';
import invoices from './invoices.json';
import plans from './plans.json';
import {loadMarketplaceState, saveMarketplaceState} from './marketplace-state';
import {loadBillingState, saveBillingState} from './state';
import {getPlanInformationPath} from 'src/libs/billing';
import type {
  BillingCard,
  Plan,
  Subscription,
} from 'src/resources/BillingResource';
import type {AxiosRequestConfig} from 'axios';

const now = Math.floor(Date.now() / 1000);

// Change these values to preview different subscription states in the dev server:
//   status: 'active'    → normal paid plan
//   status: 'trialing'  → trial with countdown (also set trialEnd below)
//   status: 'past_due'  → payment failed alert banner
//   plan: 'free'        → free plan (no price shown)
const mockSubscription: Subscription = {
  hasSubscription: true,
  isExistingCustomer: true,
  plan: 'bus-medium-2018',
  usedPrivateRepos: 12,
  status: 'active',
  trialStart: null,
  trialEnd: null, // set to: now + 5 * 24 * 60 * 60  to preview trial state
  currentPeriodEnd: now + 30 * 24 * 60 * 60,
};

const mockPlans: {plans: Plan[]} = {
  // Match the active, visible Stripe catalog in data/billing.py.
  plans,
};

const mockInvoices = {invoices};

function namespaceFor(request: AxiosRequestConfig): string {
  const org = request.url.match(/\/organization\/([^/]+)\//);
  return org ? decodeURIComponent(org[1]) : 'user1';
}

function subscriptionFor(request: AxiosRequestConfig): Subscription {
  const {plan} = loadBillingState(namespaceFor(request));
  const free =
    mockPlans.plans.find((entry) => entry.stripeId === plan)?.price === 0;
  return {
    ...mockSubscription,
    plan,
    hasSubscription: !free,
    currentPeriodEnd: free ? null : mockSubscription.currentPeriodEnd,
  };
}

const planPath = /\/api\/v1\/(user|organization\/[^/]+)\/plan$/;
const cardPath = /\/api\/v1\/(user|organization\/[^/]+)\/card$/;
const privatePath = /\/api\/v1\/(user|organization\/[^/]+)\/private$/;
const methodsPath =
  /\/api\/v1\/(user|organization\/[^/]+)\/prototype\/payment-methods$/;

mock.onGet('/api/v1/plans/').reply(200, mockPlans);
mock.onGet(planPath).reply((request) => [200, subscriptionFor(request)]);
mock.onPost(planPath).reply((request) => {
  const {plan, success_url, cancel_url} = JSON.parse(request.data) as {
    plan: string;
    success_url: string;
    cancel_url: string;
  };
  if (
    !success_url ||
    !cancel_url ||
    !mockPlans.plans.some((entry) => entry.stripeId === plan)
  ) {
    return [
      400,
      {
        error_message:
          'Select an available plan and provide checkout return URLs.',
      },
    ];
  }
  return [
    200,
    {
      url: `${window.location.origin}${getPlanInformationPath(
        namespaceFor(request),
      )}&prototypeCheckout=1&checkoutPlan=${encodeURIComponent(plan)}`,
    },
  ];
});
mock.onPut(planPath).reply((request) => {
  const {plan} = JSON.parse(request.data) as {plan: string};
  if (!mockPlans.plans.some((entry) => entry.stripeId === plan)) {
    return [400, {error_message: 'This plan is unavailable.'}];
  }
  const namespace = namespaceFor(request);
  saveBillingState(namespace, {...loadBillingState(namespace), plan});
  return [200, subscriptionFor(request)];
});

mock.onGet(cardPath).reply((request) => {
  const state = loadBillingState(namespaceFor(request));
  return [
    200,
    {
      card:
        state.methods.find((method) => method.id === state.defaultId) ?? null,
    },
  ];
});
// Simulate the URL returned by Quay's existing Stripe setup-session endpoint.
mock.onPost(cardPath).reply((request) => {
  const {success_url, cancel_url} = JSON.parse(request.data) as {
    success_url: string;
    cancel_url: string;
  };
  if (!success_url || !cancel_url) {
    return [400, {error_message: 'Checkout return URLs are required.'}];
  }
  return [
    200,
    {
      url: `${window.location.origin}${getPlanInformationPath(
        namespaceFor(request),
      )}&prototypeCheckout=1`,
    },
  ];
});
mock.onGet(methodsPath).reply((request) => {
  const {methods, defaultId} = loadBillingState(namespaceFor(request));
  return [200, {methods, defaultId}];
});
mock.onPut(methodsPath).reply((request) => {
  const namespace = namespaceFor(request);
  const state = loadBillingState(namespace);
  const {id} = JSON.parse(request.data) as {id: string};
  if (!state.methods.some((method) => method.id === id)) {
    return [400, {error_message: 'Select an available payment method.'}];
  }
  saveBillingState(namespace, {...state, defaultId: id});
  return [200, {}];
});
mock.onPost(methodsPath).reply((request) => {
  const namespace = namespaceFor(request);
  const state = loadBillingState(namespace);
  const card = JSON.parse(request.data) as BillingCard;
  const method = {
    id: `sample-${crypto.randomUUID()}`,
    owner: card.owner,
    type: card.type,
    last4: card.last4,
    exp_month: card.exp_month,
    exp_year: card.exp_year,
  };
  saveBillingState(namespace, {
    ...state,
    methods: [...state.methods, method],
    defaultId: method.id,
  });
  return [201, {}];
});

mock.onGet(privatePath).reply((request) => {
  const subscription = subscriptionFor(request);
  const plan = mockPlans.plans.find(
    (entry) => entry.stripeId === subscription.plan,
  );
  return [
    200,
    {
      privateAllowed: subscription.usedPrivateRepos < plan.privateRepos,
      privateCount: plan.privateRepos,
    },
  ];
});

mock.onGet('/api/v1/user/invoices').reply(200, mockInvoices);
mock.onGet(/\/api\/v1\/organization\/[^/]+\/invoices/).reply(200, mockInvoices);

const marketplacePath = /\/api\/v1\/organization\/([^/]+)\/marketplace$/;
const removalPath =
  /\/api\/v1\/organization\/([^/]+)\/marketplace\/batchremove$/;
mock
  .onGet('/api/v1/user/marketplace')
  .reply(() => [200, loadMarketplaceState()]);
mock.onGet(marketplacePath).reply((request) => {
  const namespace = namespaceFor(request);
  return [
    200,
    loadMarketplaceState()
      .filter((subscription) => subscription.assigned_to_org === namespace)
      .map((subscription) => ({
        ...subscription,
        subscription_id: subscription.id,
        id: `binding-${subscription.id}`,
      })),
  ];
});
function updateMarketplaceBindings(
  request: AxiosRequestConfig,
  attach: boolean,
) {
  const namespace = namespaceFor(request);
  const body = JSON.parse(request.data) as {
    subscriptions: {subscription_id: string; quantity?: number}[];
  };
  const subscriptions = loadMarketplaceState();
  if (!body.subscriptions?.length)
    return [400, {error_message: 'Select a subscription.'}];
  for (const binding of body.subscriptions) {
    const subscription = subscriptions.find(
      (entry) => entry.id === binding.subscription_id,
    );
    if (
      !subscription ||
      (attach
        ? subscription.assigned_to_org != null
        : subscription.assigned_to_org !== namespace)
    )
      return [400, {error_message: 'This subscription is unavailable.'}];
    // The sample subscriptions use SKUs that must be attached in full.
    if (binding.quantity != null && binding.quantity !== subscription.quantity)
      return [
        400,
        {error_message: 'Attach the full sample subscription quantity.'},
      ];
    subscription.assigned_to_org = attach ? namespace : null;
  }
  saveMarketplaceState(subscriptions);
  return [200, {success: true}];
}
mock
  .onPost(marketplacePath)
  .reply((request) => updateMarketplaceBindings(request, true));
mock
  .onPost(removalPath)
  .reply((request) => updateMarketplaceBindings(request, false));
