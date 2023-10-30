import {useMutation, useQueryClient} from '@tanstack/react-query';
import {convert, ConvertUserRequest} from 'src/resources/UserResource';

export function useConvertAccount({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const convertAccountMutator = useMutation(
    async ({adminUser, adminPassword}: ConvertUserRequest) => {
      return convert({adminUser, adminPassword});
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
    convert: async (convertUserRequest: ConvertUserRequest) =>
      convertAccountMutator.mutate(convertUserRequest),
    loading: convertAccountMutator.isLoading,
    error: convertAccountMutator.error,
    clientKey: convertAccountMutator.data,
  };
}
