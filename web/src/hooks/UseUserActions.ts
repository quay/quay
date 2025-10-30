import {useMutation, useQueryClient} from '@tanstack/react-query';
import {
  updateSuperuserUser,
  deleteSuperuserUser,
  UpdateSuperuserUserRequest,
} from 'src/resources/UserResource';

export function useChangeUserEmail({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const changeEmailMutator = useMutation(
    async ({username, email}: {username: string; email: string}) => {
      return await updateSuperuserUser(username, {email});
    },
    {
      onSuccess: () => {
        // Invalidate the main organizations list queries
        queryClient.invalidateQueries([
          'organization',
          'superuser',
          'organizations',
        ]);
        queryClient.invalidateQueries(['organization', 'superuser', 'users']);
        queryClient.invalidateQueries(['user']);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    changeEmail: async (username: string, email: string) =>
      changeEmailMutator.mutate({username, email}),
    isLoading: changeEmailMutator.isLoading,
  };
}

export function useChangeUserPassword({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const changePasswordMutator = useMutation(
    async ({username, password}: {username: string; password: string}) => {
      return await updateSuperuserUser(username, {password});
    },
    {
      onSuccess: () => {
        // Invalidate the main organizations list queries
        queryClient.invalidateQueries([
          'organization',
          'superuser',
          'organizations',
        ]);
        queryClient.invalidateQueries(['organization', 'superuser', 'users']);
        queryClient.invalidateQueries(['user']);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    changePassword: async (username: string, password: string) =>
      changePasswordMutator.mutate({username, password}),
    isLoading: changePasswordMutator.isLoading,
  };
}

export function useToggleUserStatus({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const toggleStatusMutator = useMutation(
    async ({username, enabled}: {username: string; enabled: boolean}) => {
      return await updateSuperuserUser(username, {enabled});
    },
    {
      onSuccess: () => {
        // Invalidate the main organizations list queries
        queryClient.invalidateQueries([
          'organization',
          'superuser',
          'organizations',
        ]);
        queryClient.invalidateQueries(['organization', 'superuser', 'users']);
        queryClient.invalidateQueries(['user']);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    toggleStatus: async (username: string, enabled: boolean) =>
      toggleStatusMutator.mutate({username, enabled}),
    isLoading: toggleStatusMutator.isLoading,
  };
}

export function useDeleteUser({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const deleteUserMutator = useMutation(
    async (username: string) => {
      return await deleteSuperuserUser(username);
    },
    {
      onSuccess: () => {
        // Invalidate the main organizations list queries
        queryClient.invalidateQueries([
          'organization',
          'superuser',
          'organizations',
        ]);
        queryClient.invalidateQueries(['organization', 'superuser', 'users']);
        queryClient.invalidateQueries(['user']);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    deleteUser: async (username: string) => deleteUserMutator.mutate(username),
    isLoading: deleteUserMutator.isLoading,
  };
}
