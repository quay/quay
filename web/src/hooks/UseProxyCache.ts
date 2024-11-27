import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  createProxyCacheConfig,
  deleteProxyCacheConfig,
  fetchProxyCacheConfig,
  validateProxyCacheConfig,
} from 'src/resources/ProxyCacheResource';
import {useCurrentUser} from './UseCurrentUser';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {AxiosError} from 'axios';

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
      onError: (err: AxiosError) => {
        onError(addDisplayError('proxy cache validation error', err));
      },
    },
  );
  return {
    proxyCacheConfigValidation,
  };
}

export function useCreateProxyCacheConfig({onSuccess, onError}) {
  const queryClient = useQueryClient();
  const {mutate: createProxyCacheConfigMutation} = useMutation(
    async (proxyCacheConfig: IProxyCacheConfig) => {
      return createProxyCacheConfig(proxyCacheConfig);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['proxycacheconfig']);
      },
      onError: (err: AxiosError) => {
        onError(addDisplayError('proxy cache creation error', err));
      },
    },
  );

  return {
    createProxyCacheConfigMutation,
  };
}

export function useDeleteProxyCacheConfig(orgName, {onSuccess, onError}) {
  const queryClient = useQueryClient();
  const {mutate: deleteProxyCacheConfigMutation} = useMutation(
    async () => {
      return deleteProxyCacheConfig(orgName);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['proxycacheconfig']);
      },
      onError: (err: AxiosError) => {
        onError(addDisplayError('proxy cache deletion error', err));
      },
    },
  );
  return {
    deleteProxyCacheConfigMutation,
  };
}
