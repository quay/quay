import axios from 'src/libs/axios';
import type {BillingCard} from './BillingResource';

export interface PrototypePaymentMethod extends BillingCard {
  id: string;
}

export interface PrototypePaymentMethods {
  methods: PrototypePaymentMethod[];
  defaultId: string | null;
}

function paymentMethodsPath(org: string | null): string {
  if (process.env.MOCK_API !== 'true') {
    throw new Error(
      'Sample payment methods are only available in the prototype.',
    );
  }
  const namespace = org ? `organization/${encodeURIComponent(org)}` : 'user';
  return `/api/v1/${namespace}/prototype/payment-methods`;
}

export async function fetchPrototypePaymentMethods(
  org: string | null,
): Promise<PrototypePaymentMethods> {
  const response = await axios.get<PrototypePaymentMethods>(
    paymentMethodsPath(org),
  );
  return response.data;
}

export async function selectPrototypePaymentMethod(
  id: string,
  org: string | null,
): Promise<void> {
  await axios.put(paymentMethodsPath(org), {id});
}

export async function addPrototypePaymentMethod(
  card: BillingCard,
  org: string | null,
): Promise<void> {
  // Explicitly send the summary fields, never the temporary form values.
  await axios.post(paymentMethodsPath(org), {
    owner: card.owner,
    type: card.type,
    last4: card.last4,
    exp_month: card.exp_month,
    exp_year: card.exp_year,
  });
}
