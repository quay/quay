import type {BillingCard} from 'src/resources/BillingResource';

type SamplePaymentMethod = BillingCard & {id: string};

export type MockBillingState = {
  plan: string;
  methods: SamplePaymentMethod[];
  defaultId: string | null;
};

export function initialBillingState(): MockBillingState {
  return {
    plan: 'bus-medium-2018',
    methods: [
      {
        id: 'visa-4242',
        owner: 'Jane Smith',
        type: 'Visa',
        last4: '4242',
        exp_month: 12,
        exp_year: 2029,
      },
      {
        id: 'mastercard-4444',
        owner: 'Jane Smith',
        type: 'Mastercard',
        last4: '4444',
        exp_month: 8,
        exp_year: 2030,
      },
    ],
    defaultId: 'visa-4242',
  };
}

export function loadBillingState(namespace: string): MockBillingState {
  try {
    const saved = localStorage.getItem(
      `quay-billing-prototype-v1:${namespace}`,
    );
    if (saved) {
      const state = JSON.parse(saved) as MockBillingState;
      if (
        typeof state.plan === 'string' &&
        Array.isArray(state.methods) &&
        (state.defaultId === null ||
          state.methods.some((method) => method.id === state.defaultId))
      ) {
        return state;
      }
    }
  } catch {
    // Browsing without storage still allows the default preview to render.
  }
  return initialBillingState();
}

export function saveBillingState(
  namespace: string,
  state: MockBillingState,
): void {
  localStorage.setItem(
    `quay-billing-prototype-v1:${namespace}`,
    JSON.stringify(state),
  );
}
