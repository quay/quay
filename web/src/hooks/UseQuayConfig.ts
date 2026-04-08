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

// New hook that also returns loading state for components that need to show loading UI
export function useQuayConfigWithLoading() {
  const {
    data: config,
    isLoading,
    error,
  } = useQuery(['config'], fetchQuayConfig, {
    staleTime: Infinity,
  });

  return {config, isLoading, error};
}
