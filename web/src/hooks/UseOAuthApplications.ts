import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {useState} from 'react';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {
  bulkDeleteOAuthApplications,
  createOAuthApplication,
  deleteOAuthApplication,
  fetchOAuthApplications,
  updateOAuthApplication,
} from 'src/resources/OAuthApplicationResource';
import {oauthApplicationColumnName} from 'src/routes/OrganizationsList/Organization/Tabs/OAuthApplications/OAuthApplicationsList';

export interface IOAuthApplication {
  application_uri: string;
  avatar_email: string;
  client_id: string;
  client_secret: string;
  description: string;
  name: string;
  redirect_uri: string;
}

export interface CreateOAuthApplicationParams {
  name: string;
  redirect_uri: string;
  application_uri: string;
  description: string;
  avatar_email: string;
}

export function useFetchOAuthApplications(org: string) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [search, setSearch] = useState<SearchState>({
    query: '',
    field: oauthApplicationColumnName.name,
  });

  const {
    data: oauthApplications,
    isError: errorLoadingOAuthApplications,
    isLoading: loadingOAuthApplications,
    isPlaceholderData,
  } = useQuery<IOAuthApplication[]>(
    ['oauthapplications', org],
    () => fetchOAuthApplications(org),
    {
      placeholderData: [],
    },
  );

  const filteredOAuthApplications =
    search.query !== ''
      ? oauthApplications?.filter((permission) =>
          permission.name.includes(search.query),
        )
      : oauthApplications;

  const paginatedOAuthApplications = filteredOAuthApplications?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  return {
    loading: loadingOAuthApplications || isPlaceholderData,
    errorLoadingOAuthApplications,
    oauthApplications,
    paginatedOAuthApplications,
    filteredOAuthApplications,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  };
}

export function useUpdateOAuthApplication(org: string) {
  const queryClient = useQueryClient();
  const {
    mutate: setOAuthApplication,
    isError: errorSetOAuthApplication,
    isSuccess: successSetOAuthApplication,
    reset: resetSetOAuthApplication,
  } = useMutation(
    async ({id, newRole}: {id: string; newRole: string}) => {
      return updateOAuthApplication(org, id, newRole);
    },
    {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries(['oauthapplications']);
      },
    },
  );
  return {
    setOAuthApplication,
    errorSetOAuthApplication,
    successSetOAuthApplication,
    resetSetOAuthApplication,
  };
}

export function useDeleteOAuthApplication(org: string) {
  const queryClient = useQueryClient();
  const {
    mutate: removeOAuthApplication,
    isError: errorDeleteOAuthApplication,
    isSuccess: successDeleteOAuthApplication,
    reset: resetDeleteOAuthApplication,
  } = useMutation(
    async ({perm}: {perm: IOAuthApplication}) => {
      return deleteOAuthApplication(org, perm);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['oauthapplications']);
      },
    },
  );
  return {
    removeOAuthApplication,
    errorDeleteOAuthApplication,
    successDeleteOAuthApplication,
    resetDeleteOAuthApplication,
  };
}

export function useCreateOAuthApplication(orgName, {onError, onSuccess}) {
  const queryClient = useQueryClient();

  const createOAuthApplicationMutator = useMutation(
    async (params: CreateOAuthApplicationParams) => {
      return createOAuthApplication(orgName, params);
    },
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['oauthapplications']);
      },
      onError: () => {
        onError();
      },
    },
  );

  return {
    createOAuthApplication: async (params: CreateOAuthApplicationParams) =>
      createOAuthApplicationMutator.mutate(params),
  };
}

export function useBulkDeleteOAuthApplications({orgName, onSuccess, onError}) {
  const queryClient = useQueryClient();

  const bulkDeleteOAuthApplicationsMutator = useMutation(
    async (perms: IOAuthApplication[]) => {
      return bulkDeleteOAuthApplications(orgName, perms);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['oauthapplications']);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    // Mutations
    bulkDeleteOAuthApplications: async (perms: IOAuthApplication[]) =>
      bulkDeleteOAuthApplicationsMutator.mutate(perms),
  };
}
