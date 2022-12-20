import {useMutation, useQueryClient} from '@tanstack/react-query';
import {bulkDeleteRepositories} from 'src/resources/RepositoryResource';
import {IRepository} from 'src/resources/RepositoryResource';

export function useDeleteRepositories({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const deleteRepositoriesMutator = useMutation(
    async (repos: IRepository[]) => {
      return bulkDeleteRepositories(repos);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['organization']);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    // Mutations
    deleteRepositories: async (repos: IRepository[]) =>
      deleteRepositoriesMutator.mutate(repos),
  };
}
