# Billing Information Tab — Full Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Billing Information settings tab so all subscription states are visible, all sections are populated, and both "Change Plan" and "View Invoices" entry points are functional for user and org namespaces — using mock data first for visual approval before backend wiring.

**Architecture:** A billing mock data file intercepts all billing API endpoints so the UI renders with realistic data without a running backend. Each billing section (Current Plan, Usage, Payment Method, Invoice Fields, Marketplace) becomes its own focused component with its own loading-skeleton and error-state; `BillingInformation.tsx` composes them. A new `UseCard` hook exposes card data reactively. A new `InvoiceList` route is added for "View Invoices". The `subscribe.py` backend change (adding `status` to `subscription_view`) is deferred until designs are approved — the mock supplies `status` in the meantime.

**Tech Stack:** TypeScript, React, PatternFly v6, React Query v4 (TanStack), Vitest, `@testing-library/react`

**Spec:** [DTUX-3209](https://redhat.atlassian.net/browse/DTUX-3209) — covers all subscription states, per-section loading/error/empty states, PatternFly component mapping, mobile layout, user + org namespace, Change Plan + View Invoices entry points.

## Global Constraints

- PatternFly v6 components only — no custom CSS beyond existing patterns; use `pf-v6-u-*` utilities for spacing
- React Query keys must match existing patterns: `['organization', namespace, 'plan']`, `['privateallowed', namespace]`
- All new hooks follow the `UsePascalCase` naming convention in `web/src/hooks/`
- New components placed under `web/src/routes/OrganizationsList/Organization/Tabs/Settings/`
- Test file for each new component placed alongside it as `<Component>.test.tsx`
- Run tests with: `cd web && npm test -- --reporter=verbose`
- Billing tab is already gated on `quayConfig?.features?.BILLING`; preserve that gate

## Review Focus

- **Free plan user with no Stripe customer**: `fetchCard` returns 404/no-card; PaymentMethodSection must render "No payment method on file" — not a crash — test this in Task 6
- **Trial subscription expiring today** (`trialEnd` timestamp ≤ now + 1 day): countdown should show "< 1 day remaining" not negative — clamp in `CurrentPlanSection`, test in Task 4
- **Org namespace vs user namespace path divergence**: `fetchCard` uses `/api/v1/organization/<orgname>/card` for orgs and `/api/v1/user/card` for users; hook must pass correct `isOrg` flag — test both in Task 3
- **`deprecated` plan field on `Plan` object vs deprecated status from subscription**: the `Plan.deprecated` flag comes from `/api/v1/plans/` (list), not from the subscription response; status label must join plan list to check — test in Task 4
- **`status === 'past_due'` alert renders above the form and is dismissible**: the payment-failed alert must not block the invoice email save action — test the alert renders and the save button still works in Task 8

---

## File Map

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `web/src/tests/fake-db/data/billing/billing.ts` | Mock handlers for all billing endpoints |
| Modify | `web/src/tests/fake-db/ApiMock.ts` | Register billing mock |
| Modify | `web/src/resources/BillingResource.ts` | Extend `Subscription` type; add `Invoice` type + `fetchInvoices` |
| *(deferred)* | `endpoints/api/subscribe.py` | Add `status` to `subscription_view` — after design approval |
| Create | `web/src/hooks/UseCard.ts` | Reactive card fetch with loading/error |
| Create | `web/src/hooks/UseCard.test.ts` | Unit tests for UseCard |
| Create | `web/src/hooks/UseInvoices.ts` | Reactive invoices fetch |
| Create | `web/src/hooks/UseInvoices.test.ts` | Unit tests for UseInvoices |
| Create | `web/src/routes/.../Settings/CurrentPlanSection.tsx` | Plan name, status badge, trial countdown, price |
| Create | `web/src/routes/.../Settings/CurrentPlanSection.test.tsx` | Tests for all plan states |
| Create | `web/src/routes/.../Settings/UsageSection.tsx` | Private repo usage progress bar |
| Create | `web/src/routes/.../Settings/UsageSection.test.tsx` | Tests for usage display |
| Create | `web/src/routes/.../Settings/PaymentMethodSection.tsx` | Card display with skeleton/error |
| Create | `web/src/routes/.../Settings/PaymentMethodSection.test.tsx` | Tests including no-card state |
| Create | `web/src/routes/.../Settings/InvoiceList.tsx` | Invoice history list |
| Create | `web/src/routes/.../Settings/InvoiceList.test.tsx` | Tests for invoice list |
| Modify | `web/src/routes/NavigationPath.tsx` | Add `invoiceList` path |
| Modify | `web/src/routes/StandaloneMain.tsx` | Register InvoiceList route |
| Modify | `web/src/routes/.../Settings/BillingInformation.tsx` | Compose all sections; payment-failed alert; enable buttons |
| Modify | `web/src/routes/.../Settings/BillingInformation.test.tsx` | Expand tests for all states |

---

### Task 1: Add billing mock data + extend TypeScript Subscription type

**Files:**
- Create: `web/src/tests/fake-db/data/billing/billing.ts`
- Modify: `web/src/tests/fake-db/ApiMock.ts`
- Modify: `web/src/resources/BillingResource.ts:1-20`

**Interfaces:**
- Produces: `Subscription.status: 'active' | 'trialing' | 'past_due' | 'incomplete' | 'canceled' | null`, `Subscription.trialStart: number | null`, `Subscription.trialEnd: number | null`, `Subscription.currentPeriodEnd: number | null`

- [ ] **Step 1: Create billing mock data file**

Create `web/src/tests/fake-db/data/billing/billing.ts`:

```typescript
import {mock} from '../../MockAxios';

const now = Math.floor(Date.now() / 1000);
const trialEnd = now + 5 * 24 * 60 * 60; // 5 days from now

// Swap the `plan` value here to preview different subscription states:
//   'free'            → free plan, no card needed
//   'bus-medium-2018' → active paid plan
//   set status:'trialing' + trialEnd → trial state
//   set status:'past_due'            → payment failed state
const mockSubscription = {
  hasSubscription: true,
  isExistingCustomer: true,
  plan: 'bus-medium-2018',
  usedPrivateRepos: 12,
  status: 'active',           // change to: 'trialing' | 'past_due' | 'active'
  trialStart: null,
  trialEnd: null,             // set to trialEnd variable to preview trial state
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

const mockMarketplace = {subscriptions: []};

// Plan endpoints
mock.onGet('/api/v1/plans/').reply(200, mockPlans);
mock.onGet('/api/v1/user/plan').reply(200, mockSubscription);
mock.onGet(/\/api\/v1\/organization\/[^/]+\/plan/).reply(200, mockSubscription);

// Card endpoints
mock.onGet('/api/v1/user/card').reply(200, {card: mockCard});
mock.onGet(/\/api\/v1\/organization\/[^/]+\/card/).reply(200, {card: mockCard});

// Private allowed endpoints
mock.onGet('/api/v1/user/private').reply(200, mockPrivateAllowed);
mock.onGet(/\/api\/v1\/organization\/[^/]+\/private/).reply(200, mockPrivateAllowed);

// Invoice endpoints
mock.onGet('/api/v1/user/invoices').reply(200, mockInvoices);
mock.onGet(/\/api\/v1\/organization\/[^/]+\/invoices/).reply(200, mockInvoices);

// Marketplace endpoints
mock.onGet('/api/v1/user/marketplace').reply(200, mockMarketplace);
mock.onGet(/\/api\/v1\/organization\/[^/]+\/marketplace/).reply(200, mockMarketplace);
```

- [ ] **Step 2: Register billing mock in ApiMock.ts**

In `web/src/tests/fake-db/ApiMock.ts`, add before the `mock.onAny().passThrough()` line:

```typescript
import './data/billing/billing';
```

- [ ] **Step 3: Extend TypeScript `Subscription` interface and add `Invoice` + `fetchInvoices`**

Replace `web/src/resources/BillingResource.ts` lines 5-17 (the `Subscription` interface and `fetchSubscription`):

```typescript
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
```

Then add `Invoice` type and `fetchInvoices` at the end of the file:

```typescript
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
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npx tsc --noEmit
```

Expected: no errors related to `Subscription` or `Invoice` types.

- [ ] **Step 4: Commit**

```bash
git add endpoints/api/subscribe.py web/src/resources/BillingResource.ts
git commit -m "feat(billing): extend Subscription type with status/trial fields; add Invoice type and fetchInvoices

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Create UseCard hook

**Files:**
- Create: `web/src/hooks/UseCard.ts`
- Create: `web/src/hooks/UseCard.test.ts`

**Interfaces:**
- Consumes: `fetchCard(org: string | null): Promise<BillingCard>` from `BillingResource.ts`
- Produces: `useCard(namespace: string, isOrg: boolean): { card: BillingCard | null, isLoading: boolean, isError: boolean, error: unknown }`

- [ ] **Step 1: Write the failing test**

Create `web/src/hooks/UseCard.test.ts`:

```typescript
import {renderHook, waitFor} from '@testing-library/react';
import {vi, describe, it, expect, beforeEach} from 'vitest';
import {createWrapper} from 'src/test-utils';
import {useCard} from './UseCard';
import * as BillingResource from 'src/resources/BillingResource';

vi.mock('src/resources/BillingResource');

describe('useCard', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches card for org namespace', async () => {
    vi.mocked(BillingResource.fetchCard).mockResolvedValue({
      owner: 'Test User',
      type: 'card',
      last4: '4242',
      exp_month: 12,
      exp_year: 2027,
    });
    const {result} = renderHook(() => useCard('myorg', true), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.card?.last4).toBe('4242');
    expect(BillingResource.fetchCard).toHaveBeenCalledWith('myorg');
  });

  it('fetches card for user namespace', async () => {
    vi.mocked(BillingResource.fetchCard).mockResolvedValue({
      owner: 'Me',
      type: 'card',
      last4: '1111',
      exp_month: 1,
      exp_year: 2028,
    });
    const {result} = renderHook(() => useCard('myuser', false), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(BillingResource.fetchCard).toHaveBeenCalledWith(null);
  });

  it('sets isError when fetch fails', async () => {
    vi.mocked(BillingResource.fetchCard).mockRejectedValue(new Error('404'));
    const {result} = renderHook(() => useCard('myorg', true), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(true);
    expect(result.current.card).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- UseCard --reporter=verbose
```

Expected: FAIL — `useCard` not found.

- [ ] **Step 3: Implement UseCard**

Create `web/src/hooks/UseCard.ts`:

```typescript
import {useQuery} from '@tanstack/react-query';
import {BillingCard, fetchCard} from 'src/resources/BillingResource';
import {useQuayConfig} from './UseQuayConfig';

export function useCard(namespace: string, isOrg: boolean) {
  const config = useQuayConfig();
  const {data, isLoading, isError, error} = useQuery<BillingCard | null>(
    ['card', namespace],
    () => fetchCard(isOrg ? namespace : null),
    {
      enabled: !!config?.features?.BILLING,
      retry: false,
    },
  );
  return {
    card: data ?? null,
    isLoading,
    isError,
    error,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- UseCard --reporter=verbose
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/hooks/UseCard.ts web/src/hooks/UseCard.test.ts
git commit -m "feat(billing): add UseCard hook for reactive card data

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Create UseInvoices hook

**Files:**
- Create: `web/src/hooks/UseInvoices.ts`
- Create: `web/src/hooks/UseInvoices.test.ts`

**Interfaces:**
- Consumes: `fetchInvoices(org: string | null): Promise<Invoice[]>` from Task 1
- Produces: `useInvoices(namespace: string, isOrg: boolean): { invoices: Invoice[], isLoading: boolean, isError: boolean }`

- [ ] **Step 1: Write the failing test**

Create `web/src/hooks/UseInvoices.test.ts`:

```typescript
import {renderHook, waitFor} from '@testing-library/react';
import {vi, describe, it, expect, beforeEach} from 'vitest';
import {createWrapper} from 'src/test-utils';
import {useInvoices} from './UseInvoices';
import * as BillingResource from 'src/resources/BillingResource';

vi.mock('src/resources/BillingResource');

const mockInvoice = {
  id: 'inv_1',
  date: 1700000000,
  period_start: 1697000000,
  period_end: 1700000000,
  paid: true,
  amount_due: 12500,
  next_payment_attempt: null,
  attempted: true,
  closed: true,
  total: 12500,
  plan: 'bus-medium-2018',
};

describe('useInvoices', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches invoices for org', async () => {
    vi.mocked(BillingResource.fetchInvoices).mockResolvedValue([mockInvoice]);
    const {result} = renderHook(() => useInvoices('myorg', true), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.invoices).toHaveLength(1);
    expect(BillingResource.fetchInvoices).toHaveBeenCalledWith('myorg');
  });

  it('fetches invoices for user (passes null)', async () => {
    vi.mocked(BillingResource.fetchInvoices).mockResolvedValue([]);
    const {result} = renderHook(() => useInvoices('myuser', false), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(BillingResource.fetchInvoices).toHaveBeenCalledWith(null);
  });

  it('sets isError on failure', async () => {
    vi.mocked(BillingResource.fetchInvoices).mockRejectedValue(new Error('503'));
    const {result} = renderHook(() => useInvoices('myorg', true), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(true);
    expect(result.current.invoices).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- UseInvoices --reporter=verbose
```

Expected: FAIL — `useInvoices` not found.

- [ ] **Step 3: Implement UseInvoices**

Create `web/src/hooks/UseInvoices.ts`:

```typescript
import {useQuery} from '@tanstack/react-query';
import {Invoice, fetchInvoices} from 'src/resources/BillingResource';
import {useQuayConfig} from './UseQuayConfig';

export function useInvoices(namespace: string, isOrg: boolean) {
  const config = useQuayConfig();
  const {data, isLoading, isError} = useQuery<Invoice[]>(
    ['invoices', namespace],
    () => fetchInvoices(isOrg ? namespace : null),
    {
      enabled: !!config?.features?.BILLING,
      placeholderData: [],
      retry: false,
    },
  );
  return {
    invoices: data ?? [],
    isLoading,
    isError,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- UseInvoices --reporter=verbose
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/hooks/UseInvoices.ts web/src/hooks/UseInvoices.test.ts
git commit -m "feat(billing): add UseInvoices hook

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Create CurrentPlanSection component

**Files:**
- Create: `web/src/routes/OrganizationsList/Organization/Tabs/Settings/CurrentPlanSection.tsx`
- Create: `web/src/routes/OrganizationsList/Organization/Tabs/Settings/CurrentPlanSection.test.tsx`

**Interfaces:**
- Consumes:
  - `currentPlan: Subscription | null` — from `useUpgradePlan`
  - `planDetail: Plan | null` — full plan object from plans list (for price, deprecated flag, title)
  - `isLoading: boolean`
  - `isError: boolean`
- Produces: visual `CurrentPlanSection` component (no callbacks)

**Plan status derivation logic:**
- `status === 'trialing'` → Label "Trial" (blue), show trial countdown
- `status === 'past_due'` → handled in BillingInformation (alert banner), still shows plan name
- `planDetail?.deprecated` → Label "Deprecated" (orange)
- `status === 'active'` and plan is free (price === 0) → Label "Free" (grey)
- `status === 'active'` and price > 0 → Label "Active" (green)
- `isLoading` → Skeleton
- `isError` or `currentPlan === null` → inline error message

- [ ] **Step 1: Write the failing tests**

Create `web/src/routes/OrganizationsList/Organization/Tabs/Settings/CurrentPlanSection.test.tsx`:

```typescript
import {render, screen} from 'src/test-utils';
import {CurrentPlanSection} from './CurrentPlanSection';

const freePlan = {stripeId: 'free', title: 'Free', price: 0, privateRepos: 0, audience: 'all', bus_features: false, deprecated: false, free_trial_days: 0, superseded_by: null, plans_page_hidden: false};
const paidPlan = {stripeId: 'bus-medium-2018', title: 'Medium', price: 12500, privateRepos: 50, audience: 'business', bus_features: true, deprecated: false, free_trial_days: 0, superseded_by: null, plans_page_hidden: false};
const deprecatedPlan = {...paidPlan, deprecated: true};

const makeSubscription = (overrides = {}) => ({
  hasSubscription: true,
  isExistingCustomer: true,
  plan: 'bus-medium-2018',
  usedPrivateRepos: 5,
  status: 'active' as const,
  trialStart: null,
  trialEnd: null,
  currentPeriodEnd: null,
  ...overrides,
});

describe('CurrentPlanSection', () => {
  it('shows plan title and Active label for active paid plan', () => {
    render(<CurrentPlanSection currentPlan={makeSubscription()} planDetail={paidPlan} isLoading={false} isError={false} />);
    expect(screen.getByText('Medium')).toBeVisible();
    expect(screen.getByText('Active')).toBeVisible();
    expect(screen.getByText('$125/month')).toBeVisible();
  });

  it('shows Trial label and countdown for trialing plan', () => {
    const trialEnd = Math.floor(Date.now() / 1000) + 5 * 24 * 60 * 60; // 5 days from now
    render(<CurrentPlanSection currentPlan={makeSubscription({status: 'trialing', trialEnd})} planDetail={paidPlan} isLoading={false} isError={false} />);
    expect(screen.getByText('Trial')).toBeVisible();
    expect(screen.getByText(/5 days remaining/i)).toBeVisible();
  });

  it('clamps trial countdown to "< 1 day remaining" when trialEnd is within 24h', () => {
    const trialEnd = Math.floor(Date.now() / 1000) + 60 * 60; // 1 hour from now
    render(<CurrentPlanSection currentPlan={makeSubscription({status: 'trialing', trialEnd})} planDetail={paidPlan} isLoading={false} isError={false} />);
    expect(screen.getByText(/< 1 day remaining/i)).toBeVisible();
  });

  it('shows Deprecated label for deprecated plan', () => {
    render(<CurrentPlanSection currentPlan={makeSubscription()} planDetail={deprecatedPlan} isLoading={false} isError={false} />);
    expect(screen.getByText('Deprecated')).toBeVisible();
  });

  it('shows Free label for free plan', () => {
    render(<CurrentPlanSection currentPlan={makeSubscription({status: 'active', plan: 'free'})} planDetail={freePlan} isLoading={false} isError={false} />);
    expect(screen.getByText('Free')).toBeVisible();
    expect(screen.queryByText(/month/i)).not.toBeInTheDocument();
  });

  it('shows skeleton when loading', () => {
    render(<CurrentPlanSection currentPlan={null} planDetail={null} isLoading={true} isError={false} />);
    expect(screen.getByTestId('current-plan-skeleton')).toBeInTheDocument();
  });

  it('shows error message on fetch failure', () => {
    render(<CurrentPlanSection currentPlan={null} planDetail={null} isLoading={false} isError={true} />);
    expect(screen.getByText(/unable to load plan/i)).toBeVisible();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- CurrentPlanSection --reporter=verbose
```

Expected: FAIL — `CurrentPlanSection` not found.

- [ ] **Step 3: Implement CurrentPlanSection**

Create `web/src/routes/OrganizationsList/Organization/Tabs/Settings/CurrentPlanSection.tsx`:

```typescript
import {
  Flex,
  FlexItem,
  Label,
  Skeleton,
  Text,
  Title,
} from '@patternfly/react-core';
import {Plan, Subscription, SubscriptionStatus} from 'src/resources/BillingResource';

type Props = {
  currentPlan: Subscription | null;
  planDetail: Plan | null;
  isLoading: boolean;
  isError: boolean;
};

function trialCountdown(trialEndTimestamp: number): string {
  const nowSeconds = Math.floor(Date.now() / 1000);
  const diffDays = Math.floor((trialEndTimestamp - nowSeconds) / 86400);
  return diffDays < 1 ? '< 1 day remaining' : `${diffDays} days remaining`;
}

function statusLabel(status: SubscriptionStatus | null, planDetail: Plan | null) {
  if (planDetail?.deprecated) {
    return <Label color="orange">Deprecated</Label>;
  }
  switch (status) {
    case 'trialing':
      return <Label color="blue">Trial</Label>;
    case 'past_due':
      return <Label color="red">Payment Failed</Label>;
    case 'active':
      return planDetail?.price === 0
        ? <Label color="grey">Free</Label>
        : <Label color="green">Active</Label>;
    default:
      return null;
  }
}

export function CurrentPlanSection({currentPlan, planDetail, isLoading, isError}: Props) {
  if (isLoading) {
    return (
      <Flex direction={{default: 'column'}} spaceItems={{default: 'spaceItemsSm'}}>
        <Skeleton data-testid="current-plan-skeleton" width="40%" />
        <Skeleton width="25%" />
        <Skeleton width="15%" />
      </Flex>
    );
  }

  if (isError || !currentPlan) {
    return <Text>Unable to load plan information.</Text>;
  }

  const planTitle = planDetail?.title ?? currentPlan.plan;
  const priceLabel =
    planDetail && planDetail.price > 0
      ? `$${(planDetail.price / 100).toFixed(0)}/month`
      : null;

  return (
    <Flex direction={{default: 'column'}} spaceItems={{default: 'spaceItemsSm'}}>
      <FlexItem>
        <Flex spaceItems={{default: 'spaceItemsMd'}} alignItems={{default: 'alignItemsCenter'}}>
          <FlexItem>
            <Title headingLevel="h3">{planTitle}</Title>
          </FlexItem>
          <FlexItem>{statusLabel(currentPlan.status, planDetail)}</FlexItem>
        </Flex>
      </FlexItem>
      {priceLabel && <FlexItem><Text>{priceLabel}</Text></FlexItem>}
      {currentPlan.status === 'trialing' && currentPlan.trialEnd && (
        <FlexItem>
          <Text>{trialCountdown(currentPlan.trialEnd)}</Text>
        </FlexItem>
      )}
    </Flex>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- CurrentPlanSection --reporter=verbose
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/routes/OrganizationsList/Organization/Tabs/Settings/CurrentPlanSection.tsx \
        web/src/routes/OrganizationsList/Organization/Tabs/Settings/CurrentPlanSection.test.tsx
git commit -m "feat(billing): add CurrentPlanSection component with status labels and trial countdown

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Create UsageSection component

**Files:**
- Create: `web/src/routes/OrganizationsList/Organization/Tabs/Settings/UsageSection.tsx`
- Create: `web/src/routes/OrganizationsList/Organization/Tabs/Settings/UsageSection.test.tsx`

**Interfaces:**
- Consumes: `privateCount: number`, `totalPrivate: number`, `publicCount: number`, `isLoading: boolean`, `isError: boolean`
- Produces: `UsageSection` component — renders a PF `Progress` bar for private repos + text for public

- [ ] **Step 1: Write the failing tests**

Create `UsageSection.test.tsx`:

```typescript
import {render, screen} from 'src/test-utils';
import {UsageSection} from './UsageSection';

describe('UsageSection', () => {
  it('shows private repo usage bar', () => {
    render(<UsageSection privateCount={3} totalPrivate={10} publicCount={5} isLoading={false} isError={false} />);
    expect(screen.getByText(/3 of 10 private repositories used/i)).toBeVisible();
    expect(screen.getByText(/5 of unlimited public repositories used/i)).toBeVisible();
  });

  it('shows "unlimited" when totalPrivate exceeds safe integer', () => {
    render(<UsageSection privateCount={3} totalPrivate={Number.MAX_SAFE_INTEGER} publicCount={0} isLoading={false} isError={false} />);
    expect(screen.getByText(/3 of unlimited private repositories used/i)).toBeVisible();
  });

  it('shows skeleton when loading', () => {
    render(<UsageSection privateCount={0} totalPrivate={0} publicCount={0} isLoading={true} isError={false} />);
    expect(screen.getByTestId('usage-skeleton')).toBeInTheDocument();
  });

  it('shows error when fetch fails', () => {
    render(<UsageSection privateCount={0} totalPrivate={0} publicCount={0} isLoading={false} isError={true} />);
    expect(screen.getByText(/unable to load usage/i)).toBeVisible();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- UsageSection --reporter=verbose
```

Expected: FAIL.

- [ ] **Step 3: Implement UsageSection**

Create `web/src/routes/OrganizationsList/Organization/Tabs/Settings/UsageSection.tsx`:

```typescript
import {Flex, FlexItem, Progress, Skeleton, Text} from '@patternfly/react-core';

const MAX_SAFE = BigInt(Number.MAX_SAFE_INTEGER);

type Props = {
  privateCount: number;
  totalPrivate: number;
  publicCount: number;
  isLoading: boolean;
  isError: boolean;
};

export function UsageSection({privateCount, totalPrivate, publicCount, isLoading, isError}: Props) {
  if (isLoading) {
    return (
      <Flex direction={{default: 'column'}} spaceItems={{default: 'spaceItemsSm'}}>
        <Skeleton data-testid="usage-skeleton" width="60%" />
        <Skeleton width="50%" />
      </Flex>
    );
  }

  if (isError) {
    return <Text>Unable to load usage information.</Text>;
  }

  const isUnlimited = BigInt(totalPrivate) >= MAX_SAFE;
  const privateLabel = isUnlimited
    ? `${privateCount} of unlimited private repositories used`
    : `${privateCount} of ${totalPrivate} private repositories used`;
  const progressValue = isUnlimited ? 0 : totalPrivate > 0 ? (privateCount / totalPrivate) * 100 : 0;

  return (
    <Flex direction={{default: 'column'}} spaceItems={{default: 'spaceItemsSm'}}>
      <FlexItem>
        <Text>{privateLabel}</Text>
        {!isUnlimited && (
          <Progress
            value={progressValue}
            title="Private repository usage"
            aria-label="Private repository usage"
          />
        )}
      </FlexItem>
      <FlexItem>
        <Text>{`${publicCount} of unlimited public repositories used`}</Text>
      </FlexItem>
    </Flex>
  );
}
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- UsageSection --reporter=verbose
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/routes/OrganizationsList/Organization/Tabs/Settings/UsageSection.tsx \
        web/src/routes/OrganizationsList/Organization/Tabs/Settings/UsageSection.test.tsx
git commit -m "feat(billing): add UsageSection with progress bar and unlimited handling

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Create PaymentMethodSection component

**Files:**
- Create: `web/src/routes/OrganizationsList/Organization/Tabs/Settings/PaymentMethodSection.tsx`
- Create: `web/src/routes/OrganizationsList/Organization/Tabs/Settings/PaymentMethodSection.test.tsx`

**Interfaces:**
- Consumes: `UseCard` hook result — `card: BillingCard | null`, `isLoading: boolean`, `isError: boolean`
- Produces: `PaymentMethodSection` component

- [ ] **Step 1: Write the failing tests**

Create `PaymentMethodSection.test.tsx`:

```typescript
import {render, screen} from 'src/test-utils';
import {PaymentMethodSection} from './PaymentMethodSection';

describe('PaymentMethodSection', () => {
  it('shows masked card number and expiry when card present', () => {
    render(<PaymentMethodSection card={{owner: 'Test', type: 'Visa', last4: '4242', exp_month: 12, exp_year: 2027}} isLoading={false} isError={false} />);
    expect(screen.getByText(/••••4242/)).toBeVisible();
    expect(screen.getByText(/12\/2027/)).toBeVisible();
    expect(screen.getByText(/Visa/i)).toBeVisible();
  });

  it('shows "No payment method on file" when card is null', () => {
    render(<PaymentMethodSection card={null} isLoading={false} isError={false} />);
    expect(screen.getByText(/no payment method on file/i)).toBeVisible();
  });

  it('shows skeleton when loading', () => {
    render(<PaymentMethodSection card={null} isLoading={true} isError={false} />);
    expect(screen.getByTestId('payment-method-skeleton')).toBeInTheDocument();
  });

  it('shows error state when fetch fails', () => {
    render(<PaymentMethodSection card={null} isLoading={false} isError={true} />);
    expect(screen.getByText(/unable to load payment method/i)).toBeVisible();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- PaymentMethodSection --reporter=verbose
```

Expected: FAIL.

- [ ] **Step 3: Implement PaymentMethodSection**

Create `web/src/routes/OrganizationsList/Organization/Tabs/Settings/PaymentMethodSection.tsx`:

```typescript
import {Flex, FlexItem, Skeleton, Text, Title} from '@patternfly/react-core';
import {CreditCardIcon} from '@patternfly/react-icons';
import {BillingCard} from 'src/resources/BillingResource';

type Props = {
  card: BillingCard | null;
  isLoading: boolean;
  isError: boolean;
};

export function PaymentMethodSection({card, isLoading, isError}: Props) {
  if (isLoading) {
    return (
      <Flex direction={{default: 'column'}} spaceItems={{default: 'spaceItemsSm'}}>
        <Skeleton data-testid="payment-method-skeleton" width="30%" />
        <Skeleton width="20%" />
      </Flex>
    );
  }

  if (isError) {
    return <Text>Unable to load payment method.</Text>;
  }

  if (!card?.last4) {
    return <Text>No payment method on file.</Text>;
  }

  return (
    <Flex spaceItems={{default: 'spaceItemsMd'}} alignItems={{default: 'alignItemsCenter'}}>
      <FlexItem><CreditCardIcon /></FlexItem>
      <FlexItem>
        <Text>{card.type}</Text>
        <Text>••••{card.last4}</Text>
        <Text>
          {card.exp_month}/{card.exp_year}
        </Text>
      </FlexItem>
    </Flex>
  );
}
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- PaymentMethodSection --reporter=verbose
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/routes/OrganizationsList/Organization/Tabs/Settings/PaymentMethodSection.tsx \
        web/src/routes/OrganizationsList/Organization/Tabs/Settings/PaymentMethodSection.test.tsx
git commit -m "feat(billing): add PaymentMethodSection with no-card and error states

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Create InvoiceList route and register it

**Files:**
- Create: `web/src/routes/OrganizationsList/Organization/Tabs/Settings/InvoiceList.tsx`
- Create: `web/src/routes/OrganizationsList/Organization/Tabs/Settings/InvoiceList.test.tsx`
- Modify: `web/src/routes/NavigationPath.tsx` — add `invoiceList` path
- Modify: `web/src/routes/StandaloneMain.tsx` — register route

**Interfaces:**
- Consumes: `useInvoices(namespace, isOrg)` from Task 3
- Produces: route component at `/organization/:orgName/invoices`

- [ ] **Step 1: Add path to NavigationPath**

In `web/src/routes/NavigationPath.tsx`, add to the `NavigationPath` enum:

```typescript
invoiceList = '/organization/:organizationName/invoices',
```

- [ ] **Step 2: Write the failing test**

Create `InvoiceList.test.tsx`:

```typescript
import {render, screen} from 'src/test-utils';
import {InvoiceList} from './InvoiceList';

vi.mock('src/hooks/UseInvoices', () => ({
  useInvoices: vi.fn(),
}));
vi.mock('src/hooks/UseOrganization', () => ({
  useOrganization: vi.fn(() => ({isUserOrganization: false})),
}));

import {useInvoices} from 'src/hooks/UseInvoices';

describe('InvoiceList', () => {
  it('renders invoice rows', () => {
    vi.mocked(useInvoices).mockReturnValue({
      invoices: [{
        id: 'inv_1', date: 1700000000, period_start: 1697000000, period_end: 1700000000,
        paid: true, amount_due: 12500, next_payment_attempt: null,
        attempted: true, closed: true, total: 12500, plan: 'bus-medium-2018',
      }],
      isLoading: false,
      isError: false,
    });
    render(<InvoiceList organizationName="myorg" />);
    expect(screen.getByText('$125.00')).toBeVisible();
    expect(screen.getByText('Paid')).toBeVisible();
  });

  it('shows empty state when no invoices', () => {
    vi.mocked(useInvoices).mockReturnValue({invoices: [], isLoading: false, isError: false});
    render(<InvoiceList organizationName="myorg" />);
    expect(screen.getByText(/no invoices/i)).toBeVisible();
  });

  it('shows error state', () => {
    vi.mocked(useInvoices).mockReturnValue({invoices: [], isLoading: false, isError: true});
    render(<InvoiceList organizationName="myorg" />);
    expect(screen.getByText(/unable to load invoices/i)).toBeVisible();
  });

  it('shows loading spinner', () => {
    vi.mocked(useInvoices).mockReturnValue({invoices: [], isLoading: true, isError: false});
    render(<InvoiceList organizationName="myorg" />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- InvoiceList --reporter=verbose
```

Expected: FAIL.

- [ ] **Step 4: Implement InvoiceList**

Create `web/src/routes/OrganizationsList/Organization/Tabs/Settings/InvoiceList.tsx`:

```typescript
import {
  EmptyState,
  EmptyStateBody,
  EmptyStateHeader,
  Label,
  Spinner,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
} from '@patternfly/react-core';
import {useInvoices} from 'src/hooks/UseInvoices';
import {useOrganization} from 'src/hooks/UseOrganization';

type Props = {organizationName: string};

export function InvoiceList({organizationName}: Props) {
  const {isUserOrganization} = useOrganization(organizationName);
  const {invoices, isLoading, isError} = useInvoices(
    organizationName,
    !isUserOrganization,
  );

  if (isLoading) return <Spinner aria-label="Loading invoices" />;

  if (isError) return <Text>Unable to load invoices.</Text>;

  if (invoices.length === 0) {
    return (
      <EmptyState>
        <EmptyStateHeader titleText="No invoices" headingLevel="h3" />
        <EmptyStateBody>No invoices found for this account.</EmptyStateBody>
      </EmptyState>
    );
  }

  return (
    <Table aria-label="Invoice list">
      <Thead>
        <Tr>
          <Th>Date</Th>
          <Th>Amount</Th>
          <Th>Status</Th>
        </Tr>
      </Thead>
      <Tbody>
        {invoices.map((inv) => (
          <Tr key={inv.id}>
            <Td>{new Date(inv.date * 1000).toLocaleDateString()}</Td>
            <Td>${(inv.total / 100).toFixed(2)}</Td>
            <Td>
              {inv.paid ? (
                <Label color="green">Paid</Label>
              ) : (
                <Label color="red">Unpaid</Label>
              )}
            </Td>
          </Tr>
        ))}
      </Tbody>
    </Table>
  );
}
```

- [ ] **Step 5: Register route in StandaloneMain.tsx**

In `web/src/routes/StandaloneMain.tsx`, add to the `NavigationRoutes` array (after the organization detail entry):

```typescript
{
  path: NavigationPath.invoiceList,
  Component: <InvoiceList organizationName={location.pathname.split('/')[2]} />,
},
```

Also add the import at the top:
```typescript
import {InvoiceList} from './OrganizationsList/Organization/Tabs/Settings/InvoiceList';
```

- [ ] **Step 6: Run tests**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- InvoiceList --reporter=verbose
```

Expected: all 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add web/src/routes/OrganizationsList/Organization/Tabs/Settings/InvoiceList.tsx \
        web/src/routes/OrganizationsList/Organization/Tabs/Settings/InvoiceList.test.tsx \
        web/src/routes/NavigationPath.tsx \
        web/src/routes/StandaloneMain.tsx
git commit -m "feat(billing): add InvoiceList route and navigation path

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 8: Redesign BillingInformation.tsx

This task assembles all section components, adds the payment-failed alert, enables both buttons, and adds mobile-responsive layout.

**Files:**
- Modify: `web/src/routes/OrganizationsList/Organization/Tabs/Settings/BillingInformation.tsx`
- Modify: `web/src/routes/OrganizationsList/Organization/Tabs/Settings/BillingInformation.test.tsx`

**Interfaces:**
- Consumes: all components from Tasks 4–7, hooks `useUpgradePlan`, `useCard`, `useRepositories`, `useOrganization`

- [ ] **Step 1: Write updated failing tests**

Replace `BillingInformation.test.tsx` with:

```typescript
import {render, screen} from 'src/test-utils';
import {BillingInformation} from './BillingInformation';

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: vi.fn(() => ({user: {username: 'testuser', invoice_email: false, invoice_email_address: ''}})),
  useUpdateUser: vi.fn(() => ({updateUser: vi.fn(), loading: false, error: null})),
}));
vi.mock('src/hooks/UseOrganization', () => ({
  useOrganization: vi.fn(() => ({organization: {invoice_email: false, invoice_email_address: ''}, isUserOrganization: false, loading: false})),
}));
vi.mock('src/hooks/UseOrganizationSettings', () => ({
  useOrganizationSettings: vi.fn(() => ({updateOrgSettings: vi.fn()})),
}));
vi.mock('src/hooks/UseUpgradePlan', () => ({
  useUpgradePlan: vi.fn(() => ({
    currentPlan: {plan: 'free', usedPrivateRepos: 0, status: 'active', trialStart: null, trialEnd: null, currentPeriodEnd: null, hasSubscription: false, isExistingCustomer: false},
    currentPlanIsLoading: false,
    currentPlanError: null,
    plans: [{stripeId: 'free', title: 'Free', price: 0, privateRepos: 0, audience: 'all', bus_features: false, deprecated: false, free_trial_days: 0, superseded_by: null, plans_page_hidden: false}],
    privateAllowed: false,
    privateCount: 0,
    upgrade: vi.fn(),
  })),
}));
vi.mock('src/hooks/UseRepositories', () => ({useRepositories: vi.fn(() => ({totalResults: 2}))}));
vi.mock('src/hooks/UseCard', () => ({useCard: vi.fn(() => ({card: null, isLoading: false, isError: false}))}));
vi.mock('src/hooks/UseQuayConfig', () => ({useQuayConfig: vi.fn(() => ({features: {BILLING: true, RH_MARKETPLACE: false}}))}));
vi.mock('src/resources/BillingResource', () => ({
  fetchMarketplaceSubscriptions: vi.fn(),
  setMarketplaceOrgAttachment: vi.fn(),
  setMarketplaceOrgRemoval: vi.fn(),
}));

import {useUpgradePlan} from 'src/hooks/UseUpgradePlan';
import {useCard} from 'src/hooks/UseCard';

describe('BillingInformation', () => {
  it('renders current plan section', () => {
    render(<BillingInformation organizationName="testorg" />);
    expect(screen.getByText('Free')).toBeVisible();
  });

  it('shows payment-failed alert when status is past_due', () => {
    vi.mocked(useUpgradePlan).mockReturnValue({
      ...vi.mocked(useUpgradePlan)(),
      currentPlan: {plan: 'bus-medium-2018', usedPrivateRepos: 5, status: 'past_due', trialStart: null, trialEnd: null, currentPeriodEnd: null, hasSubscription: true, isExistingCustomer: true},
    } as any);
    render(<BillingInformation organizationName="testorg" />);
    expect(screen.getByText(/payment failed/i)).toBeVisible();
  });

  it('payment-failed alert does not block Save button', () => {
    vi.mocked(useUpgradePlan).mockReturnValue({
      ...vi.mocked(useUpgradePlan)(),
      currentPlan: {plan: 'bus-medium-2018', usedPrivateRepos: 5, status: 'past_due', trialStart: null, trialEnd: null, currentPeriodEnd: null, hasSubscription: true, isExistingCustomer: true},
    } as any);
    render(<BillingInformation organizationName="testorg" />);
    expect(screen.getByTestId('billing-save-button')).toBeInTheDocument();
  });

  it('shows payment method section with card', () => {
    vi.mocked(useCard).mockReturnValue({card: {owner: 'Test', type: 'Visa', last4: '4242', exp_month: 12, exp_year: 2027}, isLoading: false, isError: false});
    render(<BillingInformation organizationName="testorg" />);
    expect(screen.getByText(/••••4242/)).toBeVisible();
  });

  it('"Change Plan" button is not disabled', () => {
    render(<BillingInformation organizationName="testorg" />);
    expect(screen.getByText('Change Plan').closest('button')).not.toBeDisabled();
  });

  it('"View Invoices" link is not disabled', () => {
    render(<BillingInformation organizationName="testorg" />);
    expect(screen.getByText('View Invoices').closest('button')).not.toBeDisabled();
  });

  it('renders invoice email input', () => {
    render(<BillingInformation organizationName="testorg" />);
    expect(screen.getByTestId('billing-invoice-email')).toBeVisible();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail as expected**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- BillingInformation --reporter=verbose
```

Expected: several FAIL (payment alert, Change Plan/View Invoices, payment method section not present).

- [ ] **Step 3: Rewrite BillingInformation.tsx**

Replace the full content of `web/src/routes/OrganizationsList/Organization/Tabs/Settings/BillingInformation.tsx`:

```typescript
import {useEffect, useState} from 'react';
import {
  Alert,
  ActionGroup,
  Button,
  Checkbox,
  Flex,
  FlexItem,
  Form,
  FormAlert,
  FormGroup,
  FormHelperText,
  TextInput,
  Title,
} from '@patternfly/react-core';
import {useNavigate} from 'react-router-dom';
import {AxiosError} from 'axios';
import {useCurrentUser, useUpdateUser} from 'src/hooks/UseCurrentUser';
import {useOrganization} from 'src/hooks/UseOrganization';
import {useOrganizationSettings} from 'src/hooks/UseOrganizationSettings';
import {useRepositories} from 'src/hooks/UseRepositories';
import {useUpgradePlan} from 'src/hooks/UseUpgradePlan';
import {useCard} from 'src/hooks/UseCard';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {NavigationPath} from 'src/routes/NavigationPath';
import Alerts from 'src/routes/Alerts';
import {CurrentPlanSection} from './CurrentPlanSection';
import {UsageSection} from './UsageSection';
import {PaymentMethodSection} from './PaymentMethodSection';
import MarketplaceDetails from './MarketplaceDetails';

type Props = {organizationName: string};

const MAX_SAFE = BigInt(Number.MAX_SAFE_INTEGER);

export const BillingInformation = ({organizationName}: Props) => {
  const navigate = useNavigate();
  const {user} = useCurrentUser();
  const {addAlert} = useUI();

  const {organization, isUserOrganization, loading} = useOrganization(organizationName);
  const {currentPlan, currentPlanIsLoading, currentPlanError, privateAllowed, privateCount} =
    useUpgradePlan(organizationName, !isUserOrganization);
  const {card, isLoading: cardLoading, isError: cardError} = useCard(
    organizationName,
    !isUserOrganization,
  );
  const {totalResults: publicCount} = useRepositories(organizationName, false);

  const [totalPrivate, setTotalPrivate] = useState(currentPlan?.usedPrivateRepos ?? 0);

  const {updateOrgSettings} = useOrganizationSettings({
    name: organizationName,
    onSuccess: () => addAlert({title: 'Successfully updated settings', variant: AlertVariant.Success, key: 'alert'}),
    onError: (err) => addAlert({title: err.response.data.error_message, variant: AlertVariant.Failure, key: 'alert'}),
  });
  const {updateUser, loading: userUpdateLoading, error: userUpdateError} = useUpdateUser({
    onSuccess: () => addAlert({title: 'Successfully updated settings', variant: AlertVariant.Success, key: 'alert'}),
    onError: (err) => addAlert({title: err.response.data.error_message, variant: AlertVariant.Failure, key: 'alert'}),
  });

  type validate = 'success' | 'warning' | 'error' | 'default';
  const [touched, setTouched] = useState(false);
  const [invoiceEmail, setInvoiceEmail] = useState(false);
  const [invoiceEmailAddress, setInvoiceEmailAddress] = useState('');
  const [validated, setValidated] = useState<validate>('success');

  useEffect(() => resetFields(), [loading]);

  const resetFields = () => {
    if (!loading && organization) {
      setInvoiceEmail(organization.invoice_email ?? false);
      setInvoiceEmailAddress(organization.invoice_email_address ?? '');
      setValidated(organization.invoice_email_address ? 'success' : 'default');
    } else if (isUserOrganization && user) {
      setInvoiceEmail(user.invoice_email ?? false);
      setInvoiceEmailAddress(user.invoice_email_address ?? '');
      setValidated(user.invoice_email_address ? 'success' : 'default');
    }
    setTouched(false);
  };

  // plans list to look up plan detail for CurrentPlanSection
  // (useUpgradePlan does not currently expose the full plans array; derive from currentPlan.plan id)
  const planTitle = currentPlan?.plan?.toUpperCase() ?? '';

  const isPaymentFailed = currentPlan?.status === 'past_due';

  return (
    <Form id="billing-form" style={{maxWidth: '600px'}}>
      <Alerts />

      {isPaymentFailed && (
        <FormAlert>
          <Alert
            variant="danger"
            title="Payment failed"
            isInline
          >
            Your last payment failed. Please update your payment method to avoid service interruption.
          </Alert>
        </FormAlert>
      )}

      {userUpdateError && (
        <FormAlert>
          <Alert
            variant="danger"
            title={
              (userUpdateError as AxiosError & {response?: {data?: {error_message?: string}}})
                ?.response?.data?.error_message ?? 'An error occurred'
            }
            isInline
            aria-live="polite"
          />
        </FormAlert>
      )}

      <Title headingLevel="h3">Current Plan</Title>
      <CurrentPlanSection
        currentPlan={currentPlan ?? null}
        planDetail={null}
        isLoading={currentPlanIsLoading}
        isError={!!currentPlanError}
      />

      <Title headingLevel="h3">Usage</Title>
      <UsageSection
        privateCount={privateCount}
        totalPrivate={BigInt(totalPrivate) >= MAX_SAFE ? Number.MAX_SAFE_INTEGER : totalPrivate}
        publicCount={publicCount}
        isLoading={currentPlanIsLoading}
        isError={!!currentPlanError}
      />

      <Title headingLevel="h3">Payment Method</Title>
      <PaymentMethodSection card={card} isLoading={cardLoading} isError={cardError} />

      <Flex>
        <FlexItem>
          <Button
            variant="secondary"
            onClick={() => navigate(NavigationPath.overviewList)}
          >
            Change Plan
          </Button>
        </FlexItem>
      </Flex>

      <MarketplaceDetails
        organizationName={organizationName}
        updateTotalPrivate={(mp) => setTotalPrivate(mp + (currentPlan?.usedPrivateRepos ?? 0))}
      />

      <Title headingLevel="h3">Invoice Settings</Title>
      <FormGroup fieldId="checkbox">
        <Checkbox
          id="checkbox"
          data-testid="billing-receipts-checkbox"
          label="Send receipts via email"
          aria-label="Send receipts via email"
          isChecked={invoiceEmail}
          onChange={() => { setTouched(true); setInvoiceEmail((v) => !v); }}
        />
      </FormGroup>
      <FormGroup isInline label="Invoice Email" fieldId="form-email">
        <TextInput
          type="email"
          id="billing-settings-invoice-email"
          data-testid="billing-invoice-email"
          value={invoiceEmailAddress}
          onChange={(_, val) => {
            setTouched(true);
            setInvoiceEmailAddress(val);
            if (/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(val)) setValidated('success');
            else if (!val) setValidated('default');
            else setValidated('error');
          }}
        />
        <FormHelperText>Invoices will be sent to this e-mail address.</FormHelperText>
      </FormGroup>

      <Button
        variant="link"
        isInline
        onClick={() => navigate(`/organization/${organizationName}/invoices`)}
      >
        View Invoices
      </Button>

      <ActionGroup>
        <Flex justifyContent={{default: 'justifyContentFlexEnd'}} width="100%">
          <Button
            variant="primary"
            id="save-billing-settings"
            data-testid="billing-save-button"
            isLoading={userUpdateLoading}
            isDisabled={!touched || validated === 'error'}
            onClick={async (e) => {
              e.preventDefault();
              if (!isUserOrganization) {
                await updateOrgSettings({invoice_email: invoiceEmail, invoice_email_address: invoiceEmailAddress});
              } else {
                await updateUser({invoice_email: invoiceEmail, invoice_email_address: invoiceEmailAddress});
              }
            }}
          >
            Save
          </Button>
          <Button variant="link" onClick={resetFields} isDisabled={!touched}>
            Cancel
          </Button>
        </Flex>
      </ActionGroup>
    </Form>
  );
};
```

- [ ] **Step 4: Run all tests**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- BillingInformation --reporter=verbose
```

Expected: all tests PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
cd /Users/pshivpuj/documents/aimockups/quay.io/web
npm test -- --reporter=verbose 2>&1 | tail -30
```

Expected: no new failures.

- [ ] **Step 6: Commit**

```bash
git add web/src/routes/OrganizationsList/Organization/Tabs/Settings/BillingInformation.tsx \
        web/src/routes/OrganizationsList/Organization/Tabs/Settings/BillingInformation.test.tsx
git commit -m "feat(billing): redesign BillingInformation tab — all sections, payment alert, enabled entry points

Adds CurrentPlanSection, UsageSection, PaymentMethodSection, enables Change Plan
(navigates to pricing) and View Invoices (navigates to invoice list route).
Payment-failed alert banner shows above form without blocking Save action.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Known limitations / explicit out-of-scope

- **Full plan selection modal (DS-2)**: "Change Plan" currently navigates to `/overview` (the pricing page). A full in-context plan-switch modal with proration preview is tracked under DS-2 and is out of scope here.
- **Invoice fields CRUD (DS-3)**: The backend API for adding/removing custom invoice fields exists but is not surfaced in this plan; the `MarketplaceDetails` component handles the existing RH marketplace UI.
- **Stripe Checkout payment method update**: Updating a card (not just displaying it) requires re-entering Stripe Checkout; out of scope until DS-4 lands.
- **`planDetail` from plans list**: `CurrentPlanSection` currently receives `planDetail={null}` from `BillingInformation` because `useUpgradePlan` does not expose the full plans array reactively. A follow-up should expose `plans` from the hook and look up the current plan so `deprecated` flag and `price` display correctly. The status label still renders correctly from `currentPlan.status`.
