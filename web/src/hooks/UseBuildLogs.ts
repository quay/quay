import {useQuery, UseQueryResult} from '@tanstack/react-query';
import {
  fetchBuildLogsSuperuser,
  ISuperuserBuild,
} from 'src/resources/BuildResource';

// Fetch superuser build logs by UUID
export function useFetchBuildLogsSuperuser(
  buildUuid: string | null,
): UseQueryResult<ISuperuserBuild, Error> {
  return useQuery({
    queryKey: ['superuser-build-logs', buildUuid],
    queryFn: ({signal}) => {
      if (!buildUuid) {
        throw new Error('Build UUID is required');
      }
      return fetchBuildLogsSuperuser(buildUuid, signal);
    },
    enabled: !!buildUuid && buildUuid.length > 0,
    retry: false, // Don't retry 404s
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}
