import {useMutation, useQueryClient} from '@tanstack/react-query';
import {
  RepositoryState,
  setRepositoryState,
} from 'src/resources/RepositoryResource';

export function useRepositoryState(
  org: string,
  repo: string,
  state: RepositoryState,
) {
  const queryClient = useQueryClient();
  const {
    mutate: setState,
    isLoading: loading,
    isError: error,
  } = useMutation(
    async (state: RepositoryState) => setRepositoryState(org, repo, state),
    {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries(['repodetails', org, repo]);
      },
    },
  );

  return {
    state: state,
    setState: setState,
    loading: loading,
    error: error,
  };
}
