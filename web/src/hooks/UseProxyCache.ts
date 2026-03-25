import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  createProxyCacheConfig,
  deleteProxyCacheConfig,
  fetchProxyCacheConfig,
  validateProxyCacheConfig,
} from 'src/resources/ProxyCacheResource';
import {addDisplayError} from 'src/resources/ErrorHandling';
import {AxiosError, isAxiosError} from 'axios';

export interface IProxyCacheConfig {
  upstream_registry: string;
  expiration_s: number;
  insecure?: boolean;
  org_name?: string;
  upstream_registry_username?: string;
  upstream_registry_password?: string;
}

export function useFetchProxyCacheConfig(orgName: string, enabled = true) {
  const {
    data: fetchedProxyCacheConfig,
    isLoading: isLoadingProxyCacheConfig,
    isSuccess: isSuccessLoadingProxyCacheConfig,
    isError: isErrorProxyCacheConfig,
    error: errorLoadingProxyCacheConfig,
  } = useQuery<IProxyCacheConfig | undefined>({
    queryKey: ['proxycacheconfig', orgName],
    queryFn: async ({signal}) => {
      try {
        return await fetchProxyCacheConfig(orgName, signal);
      } catch (err) {
        if (isAxiosError(err) && err.response?.status === 404) {
          return undefined;
        }
        throw err;
      }
    },
    enabled,
  });

  return {
    fetchedProxyCacheConfig,
    isProxyCacheConfigured: !!fetchedProxyCacheConfig?.upstream_registry,
    isLoadingProxyCacheConfig,
    errorLoadingProxyCacheConfig,
    isSuccessLoadingProxyCacheConfig,
    isErrorProxyCacheConfig,
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
