import {useState} from 'react';
import {
  fetchAllRepos,
  fetchRepositoriesForNamespace,
} from 'src/resources/RepositoryResource';
import {useQuery} from '@tanstack/react-query';
import {useCurrentUser} from './UseCurrentUser';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import ColumnNames from 'src/routes/RepositoriesList/ColumnNames';

export function useRepositories(organization?: string) {
  const {user} = useCurrentUser();

  // Keep state of current search in this hook
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [search, setSearch] = useState<SearchState>({
    field: ColumnNames.name,
    query: '',
  });
  const [currentOrganization, setCurrentOrganization] = useState(organization);

  const listOfOrgNames: string[] = currentOrganization
    ? [currentOrganization]
    : user?.organizations.map((org) => org.name).concat(user.username);

  const {
    data: repositories,
    isLoading: loading,
    isPlaceholderData,
    error,
  } = useQuery(
    ['organization', organization, 'repositories'],
    currentOrganization
      ? ({signal}) => fetchRepositoriesForNamespace(currentOrganization, signal)
      : ({signal}) => fetchAllRepos(listOfOrgNames, true, signal),
    {
      placeholderData: [],
    },
  );

  return {
    // Data
    repos: repositories,

    // Fetching State
    loading: loading || isPlaceholderData || !listOfOrgNames,
    error,

    // Search Query State
    search,
    setSearch,
    page,
    setPage,
    perPage,
    setPerPage,
    organization,
    setCurrentOrganization,

    // Useful Metadata
    totalResults: repositories.length,
  };
}
