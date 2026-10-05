import {mock} from '../../MockAxios';

const now = Math.floor(Date.now() / 1000);

// Change these values to preview different subscription states in the dev server:
//   status: 'active'    → normal paid plan
//   status: 'trialing'  → trial with countdown (also set trialEnd below)
//   status: 'past_due'  → payment failed alert banner
//   plan: 'free'        → free plan (no price shown)
const mockSubscription = {
  hasSubscription: true,
  isExistingCustomer: true,
  plan: 'bus-medium-2018',
  usedPrivateRepos: 12,
  status: 'active',
  trialStart: null,
  trialEnd: null, // set to: now + 5 * 24 * 60 * 60  to preview trial state
  currentPeriodEnd: now + 30 * 24 * 60 * 60,
};

const mockCard = {
  owner: 'Jane Smith',
  type: 'Visa',
  last4: '4242',
  exp_month: 12,
  exp_year: 2027,
};

const mockPlans = {
  plans: [
    {title: 'Free', price: 0, privateRepos: 0, stripeId: 'free', audience: 'personal', bus_features: false, deprecated: false, free_trial_days: 0, superseded_by: null, plans_page_hidden: false},
    {title: 'Small', price: 1500, privateRepos: 5, stripeId: 'bus-small-2018', audience: 'business', bus_features: true, deprecated: false, free_trial_days: 30, superseded_by: null, plans_page_hidden: false},
    {title: 'Medium', price: 12500, privateRepos: 50, stripeId: 'bus-medium-2018', audience: 'business', bus_features: true, deprecated: false, free_trial_days: 30, superseded_by: null, plans_page_hidden: false},
    {title: 'Large', price: 25000, privateRepos: 125, stripeId: 'bus-large-2018', audience: 'business', bus_features: true, deprecated: false, free_trial_days: 30, superseded_by: null, plans_page_hidden: false},
  ],
};

const mockPrivateAllowed = {privateAllowed: true, privateCount: 50};

const mockInvoices = {
  invoices: [
    {id: 'inv_1', date: now - 30 * 86400, period_start: now - 60 * 86400, period_end: now - 30 * 86400, paid: true, amount_due: 12500, next_payment_attempt: null, attempted: true, closed: true, total: 12500, plan: 'bus-medium-2018'},
    {id: 'inv_2', date: now - 60 * 86400, period_start: now - 90 * 86400, period_end: now - 60 * 86400, paid: true, amount_due: 12500, next_payment_attempt: null, attempted: true, closed: true, total: 12500, plan: 'bus-medium-2018'},
    {id: 'inv_3', date: now - 90 * 86400, period_start: now - 120 * 86400, period_end: now - 90 * 86400, paid: false, amount_due: 12500, next_payment_attempt: now + 3 * 86400, attempted: true, closed: false, total: 12500, plan: 'bus-medium-2018'},
  ],
};

mock.onGet('/api/v1/plans/').reply(200, mockPlans);
mock.onGet('/api/v1/user/plan').reply(200, mockSubscription);
mock.onGet(/\/api\/v1\/organization\/[^/]+\/plan/).reply(200, mockSubscription);

mock.onGet('/api/v1/user/card').reply(200, {card: mockCard});
mock.onGet(/\/api\/v1\/organization\/[^/]+\/card/).reply(200, {card: mockCard});

mock.onGet('/api/v1/user/private').reply(200, mockPrivateAllowed);
mock.onGet(/\/api\/v1\/organization\/[^/]+\/private/).reply(200, mockPrivateAllowed);

mock.onGet('/api/v1/user/invoices').reply(200, mockInvoices);
mock.onGet(/\/api\/v1\/organization\/[^/]+\/invoices/).reply(200, mockInvoices);

const mockUserSubscriptions = [
  {
    id: 'sub_user_1',
    sku: 'MW01885',
    quantity: 2,
    assigned_to_org: 'projectquay',
    metadata: {privateRepos: 5},
  },
  {
    id: 'sub_user_2',
    sku: 'MW01885',
    quantity: 1,
    assigned_to_org: null,
    metadata: {privateRepos: 5},
  },
];

const mockOrgSubscriptions = [
  {
    id: 'sub_org_1',
    sku: 'MW01885',
    quantity: 2,
    subscription_id: 'sub_user_1',
    metadata: {privateRepos: 5},
  },
];

mock.onGet('/api/v1/user/marketplace').reply(200, mockUserSubscriptions);
mock.onGet(/\/api\/v1\/organization\/[^/]+\/marketplace/).reply(200, mockOrgSubscriptions);
