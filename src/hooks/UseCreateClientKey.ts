import {useMutation, useQueryClient} from '@tanstack/react-query';
import {createClientKey} from 'src/resources/UserResource';

export function useCreateClientKey({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const createClientKeyMutator = useMutation(
    async ({password}: {password: string}) => {
      return createClientKey(password);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['user']);
        queryClient.invalidateQueries(['organization']);
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    createClientKey: async (password: string) =>
      createClientKeyMutator.mutate({password}),
    loading: createClientKeyMutator.isLoading,
    error: createClientKeyMutator.error,
    clientKey: createClientKeyMutator.data,
  };
}
