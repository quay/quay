import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  RepositoryAutoPrunePolicy,
  createRepositoryAutoPrunePolicy,
  deleteRepositoryAutoPrunePolicy,
  fetchRepositoryAutoPrunePolicies,
  updateRepositoryAutoPrunePolicy,
} from 'src/resources/RepositoryAutoPruneResource';

export function useFetchRepositoryAutoPrunePolicies(
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
    ['repositoryautoprunepolicies', organizationName, repoName],
    ({signal}) =>
      fetchRepositoryAutoPrunePolicies(organizationName, repoName, signal),
  );

  return {
    errorFetchingRepoPolicies,
    successFetchingRepoPolicies,
    isLoadingRepoPolicies,
    repoPoliciesDataUpdatedAt,
    repoPolicies,
  };
}

export function useCreateRepositoryAutoPrunePolicy(
  organizationName: string,
  repoName: string,
) {
  const queryClient = useQueryClient();
  const {
    mutate: createRepoPolicy,
    isSuccess: successRepoPolicyCreation,
    isError: errorRepoPolicyCreation,
    error: errorDetailsRepoPolicyCreation,
  } = useMutation(
    async (policy: RepositoryAutoPrunePolicy) =>
      createRepositoryAutoPrunePolicy(organizationName, repoName, policy),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'repositoryautoprunepolicies',
          organizationName,
          repoName,
        ]);
      },
    },
  );

  return {
    createRepoPolicy,
    successRepoPolicyCreation,
    errorRepoPolicyCreation,
    errorDetailsRepoPolicyCreation,
  };
}

export function useUpdateRepositoryAutoPrunePolicy(
  organizationName: string,
  repoName: string,
) {
  const queryClient = useQueryClient();
  const {
    mutate: updateRepoPolicy,
    isSuccess: successRepoPolicyUpdation,
    isError: errorRepoPolicyUpdation,
    error: errorDetailsRepoPolicyUpdation,
  } = useMutation(
    async (policy: RepositoryAutoPrunePolicy) =>
      updateRepositoryAutoPrunePolicy(organizationName, repoName, policy),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'repositoryautoprunepolicies',
          organizationName,
          repoName,
        ]);
      },
    },
  );

  return {
    updateRepoPolicy,
    successRepoPolicyUpdation,
    errorRepoPolicyUpdation,
    errorDetailsRepoPolicyUpdation,
  };
}

export function useDeleteRepositoryAutoPrunePolicy(
  organizationName: string,
  repoName: string,
) {
  const queryClient = useQueryClient();
  const {
    mutate: deleteRepoPolicy,
    isSuccess: successRepoPolicyDeletion,
    isError: errorRepoPolicyDeletion,
    error: errorDetailsRepoPolicyDeletion,
  } = useMutation(
    async (uuid: string) =>
      deleteRepositoryAutoPrunePolicy(organizationName, repoName, uuid),
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'repositoryautoprunepolicies',
          organizationName,
          repoName,
        ]);
      },
    },
  );

  return {
    deleteRepoPolicy,
    successRepoPolicyDeletion,
    errorRepoPolicyDeletion,
    errorDetailsRepoPolicyDeletion,
  };
}
