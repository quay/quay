import {
  NamespaceAutoPrunePolicy,
  createNamespaceAutoPrunePolicy,
  deleteNamespaceAutoPrunePolicy,
  fetchNamespaceAutoPrunePolicies,
  updateNamespaceAutoPrunePolicy,
} from 'src/resources/NamespaceAutoPruneResource';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';

export function useNamespaceAutoPrunePolicies(
  namespace: string,
  isUser: boolean,
  isEnabled: boolean = true,
) {
  const {
    data: nsPolicies,
    isLoading,
    error,
    isSuccess,
    dataUpdatedAt,
  } = useQuery(
    ['namespace', 'autoprunepolicies', namespace],
    ({signal}) => fetchNamespaceAutoPrunePolicies(namespace, isUser, signal),
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

export function useCreateNamespaceAutoPrunePolicy(
  namespace: string,
  isUser: boolean,
) {
  const queryClient = useQueryClient();
  const {
    mutate: createPolicy,
    isSuccess: successCreatePolicy,
    isError: errorCreatePolicy,
    error: errorCreatePolicyDetails,
  } = useMutation(
    async (policy: NamespaceAutoPrunePolicy) =>
      createNamespaceAutoPrunePolicy(namespace, policy, isUser),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'namespace',
          'autoprunepolicies',
          namespace,
        ]);
      },
    },
  );

  return {
    createPolicy: createPolicy,
    successCreatePolicy: successCreatePolicy,
    errorCreatePolicy: errorCreatePolicy,
    errorCreatePolicyDetails: errorCreatePolicyDetails,
  };
}

export function useUpdateNamespaceAutoPrunePolicy(
  namespace: string,
  isUser: boolean,
) {
  const queryClient = useQueryClient();
  const {
    mutate: updatePolicy,
    isSuccess: successUpdatePolicy,
    isError: errorUpdatePolicy,
    error: errorUpdatePolicyDetails,
  } = useMutation(
    async (policy: NamespaceAutoPrunePolicy) =>
      updateNamespaceAutoPrunePolicy(namespace, policy, isUser),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'namespace',
          'autoprunepolicies',
          namespace,
        ]);
      },
    },
  );

  return {
    updatePolicy: updatePolicy,
    successUpdatePolicy: successUpdatePolicy,
    errorUpdatePolicy: errorUpdatePolicy,
    errorUpdatePolicyDetails: errorUpdatePolicyDetails,
  };
}

export function useDeleteNamespaceAutoPrunePolicy(
  namespace: string,
  isUser: boolean,
) {
  const queryClient = useQueryClient();
  const {
    mutate: deletePolicy,
    isSuccess: successDeletePolicy,
    isError: errorDeletePolicy,
    error: errorDeletePolicyDetails,
  } = useMutation(
    async (uuid: string) =>
      deleteNamespaceAutoPrunePolicy(namespace, uuid, isUser),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'namespace',
          'autoprunepolicies',
          namespace,
        ]);
      },
    },
  );

  return {
    deletePolicy: deletePolicy,
    successDeletePolicy: successDeletePolicy,
    errorDeletePolicy: errorDeletePolicy,
    errorDeletePolicyDetails: errorDeletePolicyDetails,
  };
}
