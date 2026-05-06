import {useQuery} from '@tanstack/react-query';
import {getManifestByDigest} from 'src/resources/TagResource';

export function useManifestByDigest(org: string, repo: string, digest: string) {
  return useQuery({
    queryKey: ['manifestByDigest', org, repo, digest],
    queryFn: () => getManifestByDigest(org, repo, digest),
    enabled: !!org && !!repo && !!digest,
    retry: 1,
  });
}
