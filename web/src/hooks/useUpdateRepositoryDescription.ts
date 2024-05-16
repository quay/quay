import {useMutation, useQueryClient} from '@tanstack/react-query';
import {setRepositoryDescription} from 'src/resources/RepositoryResource';

export function useUpdateRepositoryDescription(org: string, repo: string) {
  const queryClient = useQueryClient();
  const {
    mutate: setRepoDescription,
    isError: errorSetRepoDescription,
    isSuccess: successSetRepoDescription,
    reset: resetRepoDescription,
  } = useMutation(
    async (description: string) => {
      return setRepositoryDescription(org, repo, description);
    },
    {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries(['repodetails', org, repo]);
      },
    },
  );

  return {
    setRepoDescription: setRepoDescription,
    errorSetRepoDescription: errorSetRepoDescription,
    successSetRepoDescription: successSetRepoDescription,
    resetRepoDescription: resetRepoDescription,
  };
}
