import {fetchUser} from 'src/resources/UserResource';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {useQuayConfig} from './UseQuayConfig';
import {UpdateUserRequest, updateUser} from 'src/resources/UserResource';

export function useCurrentUser(enabled = true) {
  const config = useQuayConfig();
  const {
    data: user,
    isLoading: loading,
    error,
  } = useQuery(['user'], fetchUser, {
    staleTime: Infinity,
    enabled: enabled,
  });

  // Check both possible feature flag names for superuser support
  const superUserFeatureEnabled =
    config?.features?.SUPERUSERS_FULL_ACCESS || config?.features?.SUPER_USERS;
  // Include both regular superusers and global readonly superusers
  const isSuperUser =
    superUserFeatureEnabled &&
    (user?.super_user || user?.global_readonly_super_user);

  return {user, loading, error, isSuperUser};
}

export function useUpdateUser({onSuccess, onError}) {
  const queryClient = useQueryClient();
  const updateUserMutator = useMutation(
    async ({updateUserRequest}: {updateUserRequest: UpdateUserRequest}) => {
      return updateUser(updateUserRequest);
    },
    {
      onSuccess: (updatedUser) => {
        onSuccess(updatedUser);
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
