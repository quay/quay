import {useState} from 'react';
import {
  bulkDeleteRepositories,
  createNewRepository,
  fetchRepositories,
} from 'src/resources/RepositoryResource';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {useCurrentUser} from './UseCurrentUser';
import {IRepository} from 'src/resources/RepositoryResource';

interface createRepositoryParams {
  namespace: string;
  repository: string;
  visibility: string;
  description: string;
  repo_kind: string;
}

export function useRepositories() {
  const {user} = useCurrentUser();

  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [organization, setOrganization] = useState('');

  const listOfOrgNames: string[] = organization
    ? [organization]
    : user?.organizations.map((org) => org.name).concat(user.username);

  const {
    data: repositories,
    isLoading: loading,
    isPlaceholderData,
    error,
  } = useQuery(
    ['organization', organization, 'repositories'],
    fetchRepositories,
    {
      placeholderData: [],
    },
  );

  const queryClient = useQueryClient();

  const createRepositoryMutator = useMutation(
    async ({
      namespace,
      repository,
      visibility,
      description,
      repo_kind,
    }: createRepositoryParams) => {
      return createNewRepository(
        namespace,
        repository,
        visibility,
        description,
        repo_kind,
      );
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
    repos: repositories,
    loading: loading || isPlaceholderData,
    error,
    setPage,
    setPerPage,
    page,
    perPage,
    setOrganization,
    organization,
    totalResults: listOfOrgNames.length,
    createRepository: async (params: createRepositoryParams) =>
      createRepositoryMutator.mutate(params),
    deleteRepositories: async (repos: IRepository[]) =>
      deleteRepositoryMutator.mutate(repos),
  };
}
