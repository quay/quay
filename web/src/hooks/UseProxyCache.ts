import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  createProxyCacheConfig,
  deleteProxyCacheConfig,
  fetchProxyCacheConfig,
  validateProxyCacheConfig,
} from 'src/resources/ProxyCacheResource';
import {useCurrentUser} from './UseCurrentUser';

export interface IProxyCacheConfig {
  upstream_registry: string;
  expiration_s: number;
  insecure?: boolean;
  org_name?: string;
  upstream_registry_username?: string;
  upstream_registry_password?: string;
}

export function useFetchProxyCacheConfig(orgName: string) {
  const {user} = useCurrentUser();

  const {
    data: fetchedProxyCacheConfig,
    isLoading: isLoadingProxyCacheConfig,
    isSuccess: isSuccessLoadingProxyCacheConfig,
    isError: errorLoadingProxyCacheConfig,
  } = useQuery<IProxyCacheConfig>(
    ['proxycacheconfig'],
    ({signal}) => fetchProxyCacheConfig(orgName, signal),
    {
      enabled: !(user.username === orgName),
    },
  );

  return {
    fetchedProxyCacheConfig,
    isLoadingProxyCacheConfig,
    errorLoadingProxyCacheConfig,
    isSuccessLoadingProxyCacheConfig,
  };
}

export function useValidateProxyCacheConfig(
  proxyCacheConfig: IProxyCacheConfig,
  {onSuccess, onError},
) {
  const queryClient = useQueryClient();

  const {mutate: proxyCacheConfigValidation} = useMutation(
    async () => {
      return validateProxyCacheConfig(proxyCacheConfig);
    },
    {
      onSuccess: (response) => {
        onSuccess(response);
        queryClient.invalidateQueries(['proxycacheconfig']);
      },
      onError: (err) => {
        onError(err);
      },
    },
  );
  return {
    proxyCacheConfigValidation,
  };
}

export function useCreateProxyCacheConfig() {
  const queryClient = useQueryClient();
  const {
    mutate: createProxyCacheConfigMutation,
    isError: isErrorProxyCacheCreation,
    isSuccess: successProxyCacheCreation,
    error: proxyCacheCreationError,
  } = useMutation(
    async (proxyCacheConfig: IProxyCacheConfig) => {
      return createProxyCacheConfig(proxyCacheConfig);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['proxycacheconfig']);
      },
    },
  );

  return {
    createProxyCacheConfigMutation,
    isErrorProxyCacheCreation,
    successProxyCacheCreation,
    proxyCacheCreationError,
  };
}

export function useDeleteProxyCacheConfig(orgName) {
  const queryClient = useQueryClient();
  const {
    mutate: deleteProxyCacheConfigMutation,
    isError: isErrorProxyCacheDeletion,
    isSuccess: successProxyCacheDeletion,
    error: proxyCacheDeletionError,
  } = useMutation(
    async () => {
      return deleteProxyCacheConfig(orgName);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['proxycacheconfig']);
      },
    },
  );
  return {
    deleteProxyCacheConfigMutation,
    successProxyCacheDeletion,
    isErrorProxyCacheDeletion,
    proxyCacheDeletionError,
  };
}
