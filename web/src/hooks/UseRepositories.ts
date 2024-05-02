import {useQuery} from '@tanstack/react-query';
import {useState} from 'react';
import {useRecoilState, useRecoilValue} from 'recoil';
import {
  searchReposFilterState,
  searchReposState,
} from 'src/atoms/RepositoryState';
import {OrgSearchState} from 'src/components/toolbar/SearchTypes';
import {
  fetchAllRepos,
  fetchRepositoriesForNamespace,
} from 'src/resources/RepositoryResource';
import {useCurrentUser} from './UseCurrentUser';

export function useRepositories(organization?: string, repoKind?: string) {
  const {user} = useCurrentUser();

  // Keep state of current search in this hook
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [search, setSearch] = useRecoilState<OrgSearchState>(searchReposState);
  const searchFilter = useRecoilValue(searchReposFilterState);
  const [currentOrganization, setCurrentOrganization] = useState(organization);
  repoKind = repoKind || 'image';

  const listOfOrgNames: string[] = currentOrganization
    ? [currentOrganization]
    : user?.organizations.map((org) => org.name).concat(user.username);

  const {
    data: repos,
    error,
    isLoading: loading,
    isPlaceholderData,
  } = useQuery({
    queryKey: ['organization', organization || 'all', 'repositories', repoKind, page],
    keepPreviousData: true,
    placeholderData: [],
    queryFn: ({signal}) => {
      return currentOrganization
        ? fetchRepositoriesForNamespace(currentOrganization, repoKind, signal)
        : fetchAllRepos(listOfOrgNames, repoKind, true, signal); // TODO: can repoKind be an array?
    },
  });

  return {
    // Data
    repos: repos,

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
    totalResults: repos.length,
  };
}
