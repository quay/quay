import {useState} from 'react';
import {
  bulkDeleteRepositories,
  createNewRepository,
  fetchRepositories,
  fetchRepositoriesForNamespace,
} from 'src/resources/RepositoryResource';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {useCurrentUser} from './UseCurrentUser';
import {IRepository} from 'src/resources/RepositoryResource';
import {SearchState} from 'src/components/toolbar/SearchTypes';

interface createRepositoryParams {
  namespace: string;
  repository: string;
  visibility: string;
  description: string;
  repo_kind: string;
}

export function useRepositories(organization?: string) {
  const {user} = useCurrentUser();

  // Keep state of current search in this hook
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [search, setSearch] = useState<SearchState>({
    field: '',
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
      : fetchRepositories,
    {
      placeholderData: [],
    },
  );

  const queryClient = useQueryClient();

  const deleteRepositoryMutator = useMutation(
    async (repos: IRepository[]) => {
      return bulkDeleteRepositories(repos);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'organization',
          organization,
          'repositories',
        ]);
      },
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

    // Mutations
    deleteRepositories: async (repos: IRepository[]) =>
      deleteRepositoryMutator.mutate(repos),
  };
}
