import {NamespaceAutoPrunePolicy, createNamespaceAutoPrunePolicy, deleteNamespaceAutoPrunePolicy, fetchNamespaceAutoPrunePolicies, fetchOrg, updateNamespaceAutoPrunePolicy} from 'src/resources/OrganizationResource';
import {useMutation, useQuery} from '@tanstack/react-query';
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

export function useNamespaceAutoPrunePolicies(namespace: string){
  const {
    data: policies,
    isLoading,
    error,
    isSuccess,
  } = useQuery(['namespace', 'autoprunepolicies', namespace], ({signal}) => fetchNamespaceAutoPrunePolicies(namespace, signal));

  return {
    error,
    isSuccess,
    isLoading, 
    policies,
  };
}

export function useCreateNamespaceAutoPrunePolicy(namespace: string) {
  const {
    mutate: createPolicy,
    isSuccess: successCreatePolicy,
    isError: errorCreatePolicy,
  } = useMutation(async (policy: NamespaceAutoPrunePolicy) =>
    createNamespaceAutoPrunePolicy(namespace, policy),
  );

  return {
    createPolicy: createPolicy,
    successCreatePolicy: successCreatePolicy,
    errorCreatePolicy: errorCreatePolicy,
  };
}

export function useUpdateNamespaceAutoPrunePolicy(namespace: string) {
  const {
    mutate: updatePolicy,
    isSuccess: successUpdatePolicy,
    isError: errorUpdatePolicy,
  } = useMutation(async (policy: NamespaceAutoPrunePolicy) =>
    updateNamespaceAutoPrunePolicy(namespace, policy),
  );

  return {
    updatePolicy: updatePolicy,
    successUpdatePolicy: successUpdatePolicy,
    errorUpdatePolicy: errorUpdatePolicy,
  };
}

export function useDeleteNamespaceAutoPrunePolicy(namespace: string) {
  const {
    mutate: deletePolicy,
    isSuccess: successDeletePolicy,
    isError: errorDeletePolicy,
  } = useMutation(async (uuid: string) =>
    deleteNamespaceAutoPrunePolicy(namespace, uuid),
  );

  return {
    deletePolicy: deletePolicy,
    successDeletePolicy: successDeletePolicy,
    errorDeletePolicy: errorDeletePolicy,
  };
}
