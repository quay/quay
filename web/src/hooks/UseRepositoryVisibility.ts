import {useMutation, useQueryClient} from '@tanstack/react-query';
import {setRepositoryVisibility} from 'src/resources/RepositoryResource';

export function useRepositoryVisibility(org: string, repo: string) {
  const queryClient = useQueryClient();

  const {
    mutate: setVisibility,
    isLoading: loading,
    isError: error,
  } = useMutation(
    async (visibility: string) =>
      setRepositoryVisibility(org, repo, visibility),
    {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries(['repodetails', org, repo]);
      },
    },
  );

  return {
    setVisibility: setVisibility,
    loading: loading,
    error: error,
  };
}
