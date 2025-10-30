import {useQuery} from '@tanstack/react-query';
import {getSecurityDetails} from 'src/resources/TagResource';

export function useSecurityDetails(org: string, repo: string, digest: string) {
  return useQuery({
    queryKey: ['securityDetails', org, repo, digest],
    queryFn: () => getSecurityDetails(org, repo, digest),
    enabled: !!org && !!repo && !!digest,
    retry: 1,
  });
}
