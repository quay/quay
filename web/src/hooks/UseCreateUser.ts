import {useMutation, useQueryClient} from '@tanstack/react-query';
import {
  createSuperuserUser,
  CreateSuperuserUserRequest,
} from 'src/resources/UserResource';

interface UseCreateUserOptions {
  onSuccess?: (username: string) => void;
  onError?: (error: string) => void;
}

export function useCreateUser(options?: UseCreateUserOptions) {
  const queryClient = useQueryClient();

  const createUserMutator = useMutation(
    async (data: CreateSuperuserUserRequest) => {
      return await createSuperuserUser(data);
    },
    {
      onSuccess: (data, variables) => {
        // Invalidate organizations and users cache to trigger refresh
        queryClient.invalidateQueries([
          'organization',
          'superuser',
          'organizations',
        ]);
        queryClient.invalidateQueries(['organization', 'superuser', 'users']);
        queryClient.invalidateQueries(['user']);

        if (options?.onSuccess) {
          options.onSuccess(variables.username);
        }
      },
      onError: (error: any) => {
        const errorMessage =
          error?.response?.data?.error_message ||
          error?.response?.data?.message ||
          error?.message ||
          'Failed to create user';

        if (options?.onError) {
          options.onError(errorMessage);
        }
      },
    },
  );

  return {
    createUser: async (data: CreateSuperuserUserRequest) =>
      createUserMutator.mutate(data),
    isLoading: createUserMutator.isLoading,
    isError: createUserMutator.isError,
    error: createUserMutator.error,
  };
}
