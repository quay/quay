import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  RepositoryPolicy,
  fetchRepositoryPolicy,
  updateRepositoryPolicy,
} from 'src/resources/RepositoryPolicyResource';

export function useRepositoryPolicy(namespace: string, repo: string) {
  const {
    data: policy,
    isLoading,
    error,
    isSuccess,
    dataUpdatedAt,
  } = useQuery(['repository', 'policy', namespace, repo], ({signal}) =>
    fetchRepositoryPolicy(namespace, repo, signal),
  );
  return {
    policy,
    isLoading,
    error,
    isSuccess,
    dataUpdatedAt,
  };
}

export function useUpdateRepositoryPolicy(
  namespace: string,
  repo: string,
  {onSuccess, onError},
) {
  const queryClient = useQueryClient();
  const {mutate} = useMutation(
    async (policy: RepositoryPolicy) =>
      updateRepositoryPolicy(namespace, repo, policy),
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries([
          'repository',
          'policy',
          namespace,
          repo,
        ]);
      },
      onError: (error) => {
        onError(error);
      },
    },
  );

  return {updatePolicy: mutate};
}
