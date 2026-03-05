import {useQuery} from '@tanstack/react-query';
import {isAxiosError} from 'axios';
import {fetchProxyCacheConfig} from 'src/resources/ProxyCacheResource';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

/**
 * Hook that checks whether an organization has an active proxy cache configuration.
 * Returns false without querying when the PROXY_CACHE feature flag is disabled.
 */
export function useHasProxyCacheConfig(orgName: string) {
  const config = useQuayConfig();
  const featureEnabled = config?.features?.PROXY_CACHE ?? false;

  const {data: hasProxyCacheConfig, isLoading} = useQuery<boolean>({
    queryKey: ['proxy-cache-config-exists', orgName],
    queryFn: async () => {
      try {
        const data = await fetchProxyCacheConfig(orgName);
        // Endpoint returns 200 with empty fields when no config exists,
        // so check the content instead of relying on status code alone.
        return Boolean(data?.upstream_registry);
      } catch (err) {
        if (isAxiosError(err) && err.response?.status === 404) {
          return false;
        }
        throw err;
      }
    },
    enabled: featureEnabled,
  });

  return {
    hasProxyCacheConfig: featureEnabled ? hasProxyCacheConfig ?? false : false,
    isLoading: featureEnabled ? isLoading : false,
  };
}
