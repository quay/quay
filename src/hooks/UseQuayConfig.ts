import {fetchQuayConfig} from 'src/resources/QuayConfig';
import {useQuery} from '@tanstack/react-query';

export function useQuayConfig() {
  const {
    data: config,
    isLoading: configIsLoading,
    error,
  } = useQuery(['config'], fetchQuayConfig, {
    staleTime: Infinity,
  });

  return config;
}
