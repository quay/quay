import {useQuery} from '@tanstack/react-query';
import {useState, useCallback} from 'react';
import {useRecoilState, useRecoilValue} from 'recoil';
import {
  searchReposFilterState,
  searchReposState,
} from 'src/atoms/RepositoryState';
import {OrgSearchState} from 'src/components/toolbar/SearchTypes';
import {
  fetchAllRepos,
  fetchRepositoriesForNamespace,
  IRepository,
} from 'src/resources/RepositoryResource';
import {useCurrentUser} from './UseCurrentUser';
import {useOrganizations} from './UseOrganizations';

export function useRepositories(organization?: string) {
  const {user, isSuperUser} = useCurrentUser();
  const {organizationsTableDetails} = useOrganizations();

  // Keep state of current search in this hook
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [search, setSearch] = useRecoilState<OrgSearchState>(searchReposState);
  const searchFilter = useRecoilValue(searchReposFilterState);
  const [currentOrganization, setCurrentOrganization] = useState(organization);
  const [partialResults, setPartialResults] = useState<IRepository[]>([]);

  // Build list of namespaces to fetch repositories for
  // For superusers, use the complete organizations list (includes all orgs + users)
  // For regular users, use only their own organizations + username
  const listOfOrgNames: string[] = currentOrganization
    ? [currentOrganization]
    : isSuperUser
    ? organizationsTableDetails?.map((org) => org.name) || []
    : user?.organizations.map((org) => org.name).concat(user.username) || [];

  const handlePartialResults = useCallback((newRepos: IRepository[]) => {
    setPartialResults((prev) => [...prev, ...newRepos]);
  }, []);

  const {
    data: repos,
    error,
    isLoading: loading,
    isPlaceholderData,
  } = useQuery({
    queryKey: ['organization', organization || 'all', 'repositories'],
    keepPreviousData: true,
    placeholderData: [],
    queryFn: async ({signal}): Promise<IRepository[]> => {
      // Reset partial results at the start of a new query
      setPartialResults([]);

      const result = currentOrganization
        ? fetchRepositoriesForNamespace(currentOrganization, {
            signal,
            onPartialResult: handlePartialResults,
          })
        : fetchAllRepos(listOfOrgNames, {
            flatten: true,
            signal,
            onPartialResult: handlePartialResults,
          });

      // Ensure we always return IRepository[]
      return result as Promise<IRepository[]>;
    },
  });

  // Use partial results if available, otherwise use the final results
  const displayedRepos = partialResults.length > 0 ? partialResults : repos;

  return {
    // Data
    repos: displayedRepos,

    // Fetching State
    loading: loading || isPlaceholderData || !listOfOrgNames,
    error,

    // Search Query State
    search,
    setSearch,
    searchFilter,
    page,
    setPage,
    perPage,
    setPerPage,
    organization,
    setCurrentOrganization,

    // Useful Metadata
    totalResults: displayedRepos?.length || 0,
  };
}
