import {useQuery} from '@tanstack/react-query';
import {isAxiosError} from 'axios';
import {getOrgMirrorConfig} from 'src/resources/OrgMirrorResource';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

/**
 * Hook that checks whether an organization has an active mirror configuration.
 * Returns false without querying when the ORG_MIRROR feature flag is disabled.
 */
export function useHasOrgMirrorConfig(orgName: string) {
  const config = useQuayConfig();
  const featureEnabled = config?.features?.ORG_MIRROR ?? false;

  const {data: hasOrgMirrorConfig, isLoading} = useQuery<boolean>({
    queryKey: ['org-mirror-config-exists', orgName],
    queryFn: async () => {
      try {
        await getOrgMirrorConfig(orgName);
        return true;
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
    hasOrgMirrorConfig: featureEnabled ? hasOrgMirrorConfig ?? false : false,
    isLoading: featureEnabled ? isLoading : false,
  };
}
