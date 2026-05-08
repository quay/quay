import {useQuery} from '@tanstack/react-query';
import {isAxiosError} from 'axios';
import {getOrgMirrorConfig} from 'src/resources/OrgMirrorResource';

export function useOrgMirrorExists(orgName: string, enabled = true) {
  const {
    data: isOrgMirrored,
    isLoading,
    isSuccess,
    isError,
    error,
  } = useQuery<boolean>({
    queryKey: ['org-mirror-config-exists', orgName],
    queryFn: async () => {
      try {
        await getOrgMirrorConfig(orgName);
        return true;
      } catch (err) {
        if (
          isAxiosError(err) &&
          err.response?.status &&
          err.response.status >= 400 &&
          err.response.status < 500
        ) {
          return false;
        }
        throw err;
      }
    },
    enabled,
  });

  return {
    isOrgMirrored,
    isLoading,
    isSuccess,
    isError,
    error,
  };
}
