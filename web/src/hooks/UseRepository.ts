import {useQuery} from '@tanstack/react-query';
import {isNullOrUndefined} from 'src/libs/utils';
import {
  fetchEntityTransitivePermission,
  fetchRepositoryDetails,
} from 'src/resources/RepositoryResource';

export function useRepository(org: string, repo?: string) {
  const {data, error, isLoading, isError} = useQuery(
    ['repodetails', org, repo],
    () => fetchRepositoryDetails(org, repo),
    {enabled: !isNullOrUndefined(repo)},
  );

  return {
    repoDetails: data,
    errorLoadingRepoDetails: error,
    isLoading: isLoading,
    isError: isError,
  };
}

export function useTransitivePermissions(
  org: string,
  repo: string,
  entity?: string,
) {
  const {data, isLoading, isError, error} = useQuery(
    ['transitivepermissions', org, repo, entity],
    () => fetchEntityTransitivePermission(org, repo, entity),
    {enabled: !isNullOrUndefined(entity)},
  );

  return {
    permissions: data,
    isLoading: isLoading,
    isError: isError,
    error: error,
  };
}
