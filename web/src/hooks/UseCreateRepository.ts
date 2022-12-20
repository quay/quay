import {createNewRepository} from 'src/resources/RepositoryResource';
import {useMutation, useQueryClient} from '@tanstack/react-query';

interface createRepositoryParams {
  namespace: string;
  repository: string;
  visibility: string;
  description: string;
  repo_kind: string;
}

export function useCreateRepository({onError, onSuccess}) {
  const queryClient = useQueryClient();

  const createRepositoryMutator = useMutation(
    async ({
      namespace,
      repository,
      visibility,
      description,
      repo_kind,
    }: createRepositoryParams) => {
      return createNewRepository(
        namespace,
        repository,
        visibility,
        description,
        repo_kind,
      );
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    createRepository: async (params: createRepositoryParams) =>
      createRepositoryMutator.mutate(params),
  };
}
