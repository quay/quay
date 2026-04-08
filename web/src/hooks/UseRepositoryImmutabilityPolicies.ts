import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  ImmutabilityPolicy,
  createRepositoryImmutabilityPolicy,
  deleteRepositoryImmutabilityPolicy,
  fetchRepositoryImmutabilityPolicies,
  updateRepositoryImmutabilityPolicy,
} from 'src/resources/ImmutabilityPolicyResource';

export function useFetchRepositoryImmutabilityPolicies(
  organizationName: string,
  repoName: string,
) {
  const {
    data: repoPolicies,
    isLoading: isLoadingRepoPolicies,
    error: errorFetchingRepoPolicies,
    isSuccess: successFetchingRepoPolicies,
    dataUpdatedAt: repoPoliciesDataUpdatedAt,
  } = useQuery(
    ['repositoryimmutabilitypolicies', organizationName, repoName],
    ({signal}) =>
      fetchRepositoryImmutabilityPolicies(organizationName, repoName, signal),
  );

  return {
    errorFetchingRepoPolicies,
    successFetchingRepoPolicies,
    isLoadingRepoPolicies,
    repoPoliciesDataUpdatedAt,
    repoPolicies,
  };
}

export function useCreateRepositoryImmutabilityPolicy(
  organizationName: string,
  repoName: string,
  {
    onSuccess,
    onError,
  }: {onSuccess?: () => void; onError?: (error: unknown) => void},
) {
  const queryClient = useQueryClient();
  const {mutate: createRepoPolicy, isLoading: isCreating} = useMutation(
    async (policy: Omit<ImmutabilityPolicy, 'uuid'>) =>
      createRepositoryImmutabilityPolicy(organizationName, repoName, policy),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'repositoryimmutabilitypolicies',
          organizationName,
          repoName,
        ]);
        onSuccess?.();
      },
      onError: (error: unknown) => {
        onError?.(error);
      },
    },
  );

  return {
    createRepoPolicy,
    isCreating,
  };
}

export function useUpdateRepositoryImmutabilityPolicy(
  organizationName: string,
  repoName: string,
  {
    onSuccess,
    onError,
  }: {onSuccess?: () => void; onError?: (error: unknown) => void},
) {
  const queryClient = useQueryClient();
  const {mutate: updateRepoPolicy, isLoading: isUpdating} = useMutation(
    async (policy: ImmutabilityPolicy) =>
      updateRepositoryImmutabilityPolicy(organizationName, repoName, policy),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'repositoryimmutabilitypolicies',
          organizationName,
          repoName,
        ]);
        onSuccess?.();
      },
      onError: (error: unknown) => {
        onError?.(error);
      },
    },
  );

  return {
    updateRepoPolicy,
    isUpdating,
  };
}

export function useDeleteRepositoryImmutabilityPolicy(
  organizationName: string,
  repoName: string,
  {
    onSuccess,
    onError,
  }: {onSuccess?: () => void; onError?: (error: unknown) => void},
) {
  const queryClient = useQueryClient();
  const {mutate: deleteRepoPolicy, isLoading: isDeleting} = useMutation(
    async (uuid: string) =>
      deleteRepositoryImmutabilityPolicy(organizationName, repoName, uuid),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'repositoryimmutabilitypolicies',
          organizationName,
          repoName,
        ]);
        onSuccess?.();
      },
      onError: (error: unknown) => {
        onError?.(error);
      },
    },
  );

  return {
    deleteRepoPolicy,
    isDeleting,
  };
}
