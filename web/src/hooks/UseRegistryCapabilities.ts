import {useQuery} from '@tanstack/react-query';
import {
  fetchRegistryCapabilities,
  RegistryCapabilities,
} from 'src/resources/CapabilitiesResource';

export function useRegistryCapabilities() {
  const {
    data: capabilities,
    isLoading,
    error,
  } = useQuery<RegistryCapabilities, Error>(
    ['registryCapabilities'],
    fetchRegistryCapabilities,
    {
      staleTime: Infinity,
    },
  );
  return {capabilities, isLoading, error};
}

export function useMirrorArchitectures() {
  const {capabilities, isLoading, error} = useRegistryCapabilities();
  return {
    architectures: capabilities?.mirror_architectures ?? [],
    isLoading,
    error,
  };
}
