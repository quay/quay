import {NamespaceAutoPrunePolicy, createNamespaceAutoPrunePolicy, deleteNamespaceAutoPrunePolicy, fetchNamespaceAutoPrunePolicies, fetchOrg, updateNamespaceAutoPrunePolicy} from 'src/resources/OrganizationResource';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {useOrganizations} from './UseOrganizations';

export function useOrganization(name: string) {
  // Get usernames
  const {usernames} = useOrganizations();
  const isUserOrganization = usernames.includes(name);

  // Get organization
  const {
    data: organization,
    isLoading,
    error,
  } = useQuery(['organization', name], ({signal}) => fetchOrg(name, signal), {
    enabled: !isUserOrganization,
  });

  return {
    isUserOrganization,
    error,
    loading: isLoading,
    organization,
  };
}

export function useNamespaceAutoPrunePolicies(namespace: string, isUser: boolean){
  const {
    data: policies,
    isLoading,
    error,
    isSuccess,
    dataUpdatedAt,
  } = useQuery(['namespace', 'autoprunepolicies', namespace], 
  ({signal}) => fetchNamespaceAutoPrunePolicies(namespace, isUser, signal),
  );

  return {
    error,
    isSuccess,
    isLoading, 
    dataUpdatedAt,
    policies,
  };
}

export function useCreateNamespaceAutoPrunePolicy(namespace: string, isUser: boolean) {
  const queryClient = useQueryClient();
  const {
    mutate: createPolicy,
    isSuccess: successCreatePolicy,
    isError: errorCreatePolicy,
    error: errorCreatePolicyDetails,
  } = useMutation(async (policy: NamespaceAutoPrunePolicy) =>
    createNamespaceAutoPrunePolicy(namespace, policy, isUser),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['namespace', 'autoprunepolicies', namespace]);
      },
    }
  );

  return {
    createPolicy: createPolicy,
    successCreatePolicy: successCreatePolicy,
    errorCreatePolicy: errorCreatePolicy,
    errorCreatePolicyDetails: errorCreatePolicyDetails,
  };
}

export function useUpdateNamespaceAutoPrunePolicy(namespace: string, isUser: boolean) {
  const queryClient = useQueryClient();
  const {
    mutate: updatePolicy,
    isSuccess: successUpdatePolicy,
    isError: errorUpdatePolicy,
    error: errorUpdatePolicyDetails,
  } = useMutation(async (policy: NamespaceAutoPrunePolicy) =>
    updateNamespaceAutoPrunePolicy(namespace, policy, isUser),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['namespace', 'autoprunepolicies', namespace]);
      },
    }
  );

  return {
    updatePolicy: updatePolicy,
    successUpdatePolicy: successUpdatePolicy,
    errorUpdatePolicy: errorUpdatePolicy,
    errorUpdatePolicyDetails: errorUpdatePolicyDetails,
  };
}

export function useDeleteNamespaceAutoPrunePolicy(namespace: string, isUser: boolean) {
  const queryClient = useQueryClient();
  const {
    mutate: deletePolicy,
    isSuccess: successDeletePolicy,
    isError: errorDeletePolicy,
    error: errorDeletePolicyDetails,
  } = useMutation(async (uuid: string) =>
    deleteNamespaceAutoPrunePolicy(namespace, uuid, isUser),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['namespace', 'autoprunepolicies', namespace]);
      },
    }
  );

  return {
    deletePolicy: deletePolicy,
    successDeletePolicy: successDeletePolicy,
    errorDeletePolicy: errorDeletePolicy,
    errorDeletePolicyDetails: errorDeletePolicyDetails,
  };
}
