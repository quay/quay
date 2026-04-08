import {useMutation, useQueryClient} from '@tanstack/react-query';
import {
  createSuperuserUser,
  CreateSuperuserUserRequest,
} from 'src/resources/UserResource';

interface UseCreateUserOptions {
  onSuccess?: (username: string, password: string) => void;
  onError?: (error: any) => void;
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
          options.onSuccess(variables.username, data.password);
        }
      },
      onError: (error: any) => {
        if (options?.onError) {
          options.onError(error);
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
