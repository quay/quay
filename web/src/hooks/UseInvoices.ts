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
