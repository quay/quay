import {
  ImmutabilityPolicy,
  createNamespaceImmutabilityPolicy,
  deleteNamespaceImmutabilityPolicy,
  fetchNamespaceImmutabilityPolicies,
  updateNamespaceImmutabilityPolicy,
} from 'src/resources/ImmutabilityPolicyResource';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';

export function useNamespaceImmutabilityPolicies(
  namespace: string,
  isEnabled = true,
) {
  const {
    data: nsPolicies,
    isLoading,
    error,
    isSuccess,
    dataUpdatedAt,
  } = useQuery(
    ['namespace', 'immutabilitypolicies', namespace],
    ({signal}) => fetchNamespaceImmutabilityPolicies(namespace, signal),
    {
      enabled: isEnabled,
    },
  );

  return {
    error,
    isSuccess,
    isLoading,
    dataUpdatedAt,
    nsPolicies,
  };
}

export function useCreateNamespaceImmutabilityPolicy(
  namespace: string,
  {
    onSuccess,
    onError,
  }: {onSuccess?: () => void; onError?: (error: unknown) => void},
) {
  const queryClient = useQueryClient();
  const {mutate: createPolicy, isLoading: isCreating} = useMutation(
    async (policy: Omit<ImmutabilityPolicy, 'uuid'>) =>
      createNamespaceImmutabilityPolicy(namespace, policy),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'namespace',
          'immutabilitypolicies',
          namespace,
        ]);
        onSuccess?.();
      },
      onError: (error: unknown) => {
        onError?.(error);
      },
    },
  );

  return {
    createPolicy,
    isCreating,
  };
}

export function useUpdateNamespaceImmutabilityPolicy(
  namespace: string,
  {
    onSuccess,
    onError,
  }: {onSuccess?: () => void; onError?: (error: unknown) => void},
) {
  const queryClient = useQueryClient();
  const {mutate: updatePolicy, isLoading: isUpdating} = useMutation(
    async (policy: ImmutabilityPolicy) =>
      updateNamespaceImmutabilityPolicy(namespace, policy),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'namespace',
          'immutabilitypolicies',
          namespace,
        ]);
        onSuccess?.();
      },
      onError: (error: unknown) => {
        onError?.(error);
      },
    },
  );

  return {
    updatePolicy,
    isUpdating,
  };
}

export function useDeleteNamespaceImmutabilityPolicy(
  namespace: string,
  {
    onSuccess,
    onError,
  }: {onSuccess?: () => void; onError?: (error: unknown) => void},
) {
  const queryClient = useQueryClient();
  const {mutate: deletePolicy, isLoading: isDeleting} = useMutation(
    async (uuid: string) => deleteNamespaceImmutabilityPolicy(namespace, uuid),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'namespace',
          'immutabilitypolicies',
          namespace,
        ]);
        onSuccess?.();
      },
      onError: (error: unknown) => {
        onError?.(error);
      },
    },
  );

  return {
    deletePolicy,
    isDeleting,
  };
}
