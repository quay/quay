import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  fetchRegistrySize,
  queueRegistrySizeCalculation,
  IRegistrySize,
} from 'src/resources/RegistrySizeResource';
import {AxiosError} from 'axios';
import {addDisplayError} from 'src/resources/ErrorHandling';

// Hook to fetch registry size data
export function useRegistrySize(enabled = true) {
  const {
    data: registrySize,
    isLoading,
    error,
    refetch,
  } = useQuery<IRegistrySize>(['registrysize'], fetchRegistrySize, {
    retry: false,
    enabled: enabled,
  });

  return {
    registrySize,
    isLoading,
    error,
    refetch,
  };
}

// Hook to queue registry size calculation
export function useQueueRegistrySizeCalculation({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const {mutate: queueCalculation, isLoading: isQueuing} = useMutation(
    queueRegistrySizeCalculation,
    {
      onSuccess: () => {
        onSuccess();
        // Refresh registry size data after queuing
        queryClient.invalidateQueries(['registrysize']);
      },
      onError: (err: AxiosError) => {
        onError(
          addDisplayError('Could not queue registry size calculation', err),
        );
      },
    },
  );

  return {
    queueCalculation,
    isQueuing,
  };
}
