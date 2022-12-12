import {useMutation, useQueryClient} from '@tanstack/react-query';
import {UpdateUserRequest, updateUser} from 'src/resources/UserResource';

export function useUpdateUser({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const updateUserMutator = useMutation(
    async ({
      name,
      updateUserRequest,
    }: {
      name: string;
      updateUserRequest: UpdateUserRequest;
    }) => {
      return updateUser(name, updateUserRequest);
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
    updateUser: async (name: string, updateUserRequest: UpdateUserRequest) =>
      updateUserMutator.mutate({name, updateUserRequest}),
    loading: updateUserMutator.isLoading,
    error: updateUserMutator.error,
  };
}
