import {useQuery} from '@tanstack/react-query';
import {fetchSecurityDetails} from 'src/resources/ManifestSecurityResource';

export function useManifestSecurity(
  org: string,
  repo: string,
  digest: string,
  enabled = true,
) {
  const {
    data: securityDetails,
    isLoading: isSecurityDetailsLoading,
    isError: isSecurityDetailsError,
    error: securityDetailsError,
  } = useQuery(
    ['manifestsecurity', org, repo, digest],
    ({signal}) => fetchSecurityDetails(org, repo, digest, signal),
    {
      enabled: enabled,
      staleTime: 1000 * 60 * 5,
      cacheTime: 1000 * 60 * 15,
      retry: 3,
      retryDelay: (attempt) => attempt * 1000, // 1s, 2s, 3s
    },
  );

  return {
    securityDetails,
    isSecurityDetailsError,
    securityDetailsError,
    isSecurityDetailsLoading: isSecurityDetailsLoading,
  };
}
