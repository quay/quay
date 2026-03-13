import {useQuery} from '@tanstack/react-query';
import {isAxiosError} from 'axios';
import {fetchProxyCacheConfig} from 'src/resources/ProxyCacheResource';

export function useProxyCacheExists(orgName: string, enabled = true) {
  const {
    data: isProxyCacheConfigured,
    isLoading,
    isSuccess,
    isError,
    error,
  } = useQuery<boolean>({
    queryKey: ['proxy-cache-config-exists', orgName],
    queryFn: async () => {
      try {
        const config = await fetchProxyCacheConfig(orgName);
        return !!config?.upstream_registry;
      } catch (err) {
        if (isAxiosError(err) && err.response?.status === 404) {
          return false;
        }
        throw err;
      }
    },
    enabled,
  });

  return {
    isProxyCacheConfigured,
    isLoading,
    isSuccess,
    isError,
    error,
  };
}
