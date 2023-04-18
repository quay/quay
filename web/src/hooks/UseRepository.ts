import {useQuery} from '@tanstack/react-query';
import {fetchRepositoryDetails} from 'src/resources/RepositoryResource';

export function useRepository(org: string, repo: string) {
  const {data, error} = useQuery(['repodetails', org, repo], () =>
    fetchRepositoryDetails(org, repo),
  );

  return {
    repoDetails: data,
    errorLoadingRepoDetails: error,
  };
}
