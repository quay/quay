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
  fetchAllReposAsSuperUser,
  fetchRepositories,
  fetchRepositoriesForNamespace,
  IRepository,
  SuperUserReposResult,
} from 'src/resources/RepositoryResource';
import {useCurrentUser} from './UseCurrentUser';

export interface UseRepositoriesReturn {
  repos: IRepository[];
  loading: boolean;
  error: unknown;
  search: OrgSearchState;
  setSearch: (search: OrgSearchState) => void;
  searchFilter: (item: IRepository) => boolean;
  page: number;
  setPage: (page: number) => void;
  perPage: number;
  setPerPage: (perPage: number) => void;
  organization: string | undefined;
  setCurrentOrganization: (org: string | undefined) => void;
  totalResults: number;
  truncated: boolean;
}

export function useRepositories(organization?: string): UseRepositoriesReturn {
  const {user, isSuperUser} = useCurrentUser();

  // Keep state of current search in this hook
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [search, setSearch] = useRecoilState<OrgSearchState>(searchReposState);
  const searchFilter = useRecoilValue(searchReposFilterState);
  const [currentOrganization, setCurrentOrganization] = useState(organization);
  const [partialResults, setPartialResults] = useState<IRepository[]>([]);
  const [truncated, setTruncated] = useState(false);

  const listOfOrgNames: string[] = currentOrganization
    ? [currentOrganization]
    : user?.anonymous
      ? [] // Anonymous users have no namespaces to fetch
      : user?.organizations?.map((org) => org.name).concat(user.username) || [];

  const handlePartialResults = useCallback((newRepos: IRepository[]) => {
    setPartialResults((prev) => [...prev, ...newRepos]);
  }, []);

  const {
    data: repos,
    error,
    isLoading: loading,
    isPlaceholderData,
  } = useQuery({
    queryKey: [
      'organization',
      organization || 'all',
      'repositories',
      isSuperUser ? 'superuser' : user?.anonymous ? 'anonymous' : 'user',
    ],
    keepPreviousData: true,
    placeholderData: [],
    queryFn: async ({signal}): Promise<IRepository[]> => {
      // Reset partial results at the start of a new query
      setPartialResults([]);
      setTruncated(false);

      // Anonymous users without a specific org: show all public repos
      if (user?.anonymous && !currentOrganization) {
        return fetchRepositories();
      }

      if (currentOrganization) {
        return fetchRepositoriesForNamespace(currentOrganization, {
          signal,
          onPartialResult: handlePartialResults,
        });
      }

      // Superusers: single paginated API call returns all repos across all namespaces
      if (isSuperUser) {
        const result: SuperUserReposResult = await fetchAllReposAsSuperUser({
          signal,
          onPartialResult: handlePartialResults,
        });
        setTruncated(result.truncated);
        return result.repos;
      }

      // Normal users: fan out per namespace
      const result = await fetchAllRepos(listOfOrgNames, {
        flatten: true,
        signal,
        onPartialResult: handlePartialResults,
      });
      return result as IRepository[];
    },
  });

  // Use partial results if available, otherwise use the final results
  const displayedRepos = partialResults.length > 0 ? partialResults : repos;

  return {
    // Data
    repos: displayedRepos,

    // Fetching State
    loading: loading || isPlaceholderData || (!isSuperUser && !listOfOrgNames),
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
    truncated,
  };
}
