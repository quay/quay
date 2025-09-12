import {fetchUser} from 'src/resources/UserResource';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {useQuayConfig} from './UseQuayConfig';
import {UpdateUserRequest, updateUser} from 'src/resources/UserResource';

export function useCurrentUser() {
  const config = useQuayConfig();
  const {
    data: user,
    isLoading: loading,
    error,
  } = useQuery(['user'], fetchUser, {
    staleTime: Infinity,
  });

  const isSuperUser =
    config?.features?.SUPERUSERS_FULL_ACCESS && user?.super_user;

  return {user, loading, error, isSuperUser};
}

export function useUpdateUser({onSuccess, onError}) {
  const queryClient = useQueryClient();
  const updateUserMutator = useMutation(
    async ({updateUserRequest}: {updateUserRequest: UpdateUserRequest}) => {
      return updateUser(updateUserRequest);
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
    updateUser: async (updateUserRequest: UpdateUserRequest) =>
      updateUserMutator.mutate({updateUserRequest}),
    loading: updateUserMutator.isLoading,
    error: updateUserMutator.error,
  };
}
