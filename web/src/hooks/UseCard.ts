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
