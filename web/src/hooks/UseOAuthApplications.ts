import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {useState} from 'react';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {
  bulkDeleteOAuthApplications,
  createOAuthApplication,
  deleteOAuthApplication,
  fetchOAuthApplications,
  resetOAuthApplicationClientSecret,
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
    search.query !== '' && oauthApplications
      ? oauthApplications.filter((permission) =>
          permission.name.includes(search.query),
        )
      : oauthApplications || [];

  const paginatedOAuthApplications = filteredOAuthApplications.slice(
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

export function useUpdateOAuthApplication(
  org: string,
  onSuccess?: () => void,
  onError?: (error: unknown) => void,
) {
  const queryClient = useQueryClient();
  const {
    mutate: updateOAuthApplicationMutation,
    isError: errorUpdateOAuthApplication,
    isSuccess: successUpdateOAuthApplication,
    reset: resetUpdateOAuthApplication,
  } = useMutation(
    async ({
      clientId,
      applicationData,
    }: {
      clientId: string;
      applicationData: Partial<IOAuthApplication>;
    }) => {
      return updateOAuthApplication(org, clientId, applicationData);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['oauthapplications']);
        if (onSuccess) {
          onSuccess();
        }
      },
      onError: (error) => {
        if (onError) {
          onError(error);
        }
      },
    },
  );
  return {
    updateOAuthApplicationMutation,
    errorUpdateOAuthApplication,
    successUpdateOAuthApplication,
    resetUpdateOAuthApplication,
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
    async ({oauthApp}: {oauthApp: IOAuthApplication}) => {
      return deleteOAuthApplication(org, oauthApp);
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

export function useResetOAuthApplicationClientSecret(
  org: string,
  onSuccess?: (updatedApplication: IOAuthApplication) => void,
  onError?: (error: unknown) => void,
) {
  const queryClient = useQueryClient();
  const {
    mutate: resetOAuthApplicationClientSecretMutation,
    isError: errorResetOAuthApplicationClientSecret,
    isSuccess: successResetOAuthApplicationClientSecret,
    reset: resetResetOAuthApplicationClientSecret,
  } = useMutation(
    async (clientId: string) => {
      return resetOAuthApplicationClientSecret(org, clientId);
    },
    {
      onSuccess: (updatedApplication: IOAuthApplication) => {
        queryClient.invalidateQueries(['oauthapplications']);
        if (onSuccess) {
          onSuccess(updatedApplication);
        }
      },
      onError: (error) => {
        if (onError) {
          onError(error);
        }
      },
    },
  );
  return {
    resetOAuthApplicationClientSecretMutation,
    errorResetOAuthApplicationClientSecret,
    successResetOAuthApplicationClientSecret,
    resetResetOAuthApplicationClientSecret,
  };
}
