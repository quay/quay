import type {MarketplaceSubscription} from 'src/resources/BillingResource';

const initialSubscriptions: MarketplaceSubscription[] = [
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
const storageKey = 'quay-customer-portal-prototype-v1';

export function loadMarketplaceState(): MarketplaceSubscription[] {
  try {
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      const subscriptions = JSON.parse(saved) as MarketplaceSubscription[];
      if (Array.isArray(subscriptions)) return subscriptions;
    }
  } catch {
    // The default subscriptions also work when storage is unavailable.
  }
  return initialSubscriptions.map((subscription) => ({...subscription}));
}

export function saveMarketplaceState(
  subscriptions: MarketplaceSubscription[],
): void {
  localStorage.setItem(storageKey, JSON.stringify(subscriptions));
}
