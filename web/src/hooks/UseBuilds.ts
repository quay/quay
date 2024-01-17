import {useQuery} from '@tanstack/react-query';
import {isNullOrUndefined} from 'src/libs/utils';
import {
  fetchBuilds,
  fetchNamespaces,
  fetchRefs,
  fetchSources,
  fetchSubDirs,
} from 'src/resources/BuildResource';

export function useBuilds(
  org: string,
  repo: string,
  buildsSinceInSeconds: number = null,
) {
  const {data, isError, error, isLoading} = useQuery(
    ['repobuilds', org, repo, String(buildsSinceInSeconds)],
    () => {
      // Keeping the same calls as the old UI for now, if a filter is given fetch 100 builds
      // This can be changed after pagination has been implemented in the API
      return isNullOrUndefined(buildsSinceInSeconds)
        ? fetchBuilds(org, repo, buildsSinceInSeconds)
        : fetchBuilds(org, repo, buildsSinceInSeconds, 100);
    },
  );

  return {
    builds: data,
    isError: isError,
    error: error,
    isLoading: isLoading,
  };
}
