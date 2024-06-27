import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {useState} from 'react';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {useCurrentUser} from './UseCurrentUser';
import {superuserOrgsColumnNames} from 'src/routes/SuperuserList/Organizations/SuperuserOrgsList';
import {
  bulkDeleteOrgs,
  fetchSuperuserOrgs,
  takeOwnershipOfOrg,
  updateOrgName,
} from 'src/resources/SuperuserOrgsResource';

export interface ISuperuserOrgs {
  name: string;
  email: string;
}

export function useFetchSuperuserOrgs() {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [search, setSearch] = useState<SearchState>({
    query: '',
    field: superuserOrgsColumnNames.name,
  });
  const {isSuperUser} = useCurrentUser();

  const {
    data: orgs,
    isLoading,
    isPlaceholderData,
    isError: errorLoadingOrgs,
  } = useQuery<ISuperuserOrgs[]>(
    ['superuserorgs'],
    () => fetchSuperuserOrgs(),
    {
      placeholderData: [],
      enabled: isSuperUser || true,
    },
  );

  const filteredOrgs =
    search.query !== ''
      ? orgs?.filter((org) => org.name.includes(search.query))
      : orgs;

  const paginatedOrgs = filteredOrgs?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  return {
    orgs,
    filteredOrgs,
    paginatedOrgs,
    isLoadingOrgs: isLoading || isPlaceholderData,
    errorLoadingOrgs,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  };
}

export function useDeleteOrg({onSuccess, onError}) {
  const queryClient = useQueryClient();
  const deleteOrgsMutator = useMutation(
    async (orgs: ISuperuserOrgs[] | ISuperuserOrgs) => {
      orgs = Array.isArray(orgs) ? orgs : [orgs];
      return bulkDeleteOrgs(orgs);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['superuserorgs']);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );
  return {
    removeOrg: async (orgs: ISuperuserOrgs[] | ISuperuserOrgs) =>
      deleteOrgsMutator.mutate(orgs),
  };
}

export function useUpdateOrgName() {
  const queryClient = useQueryClient();
  const {
    mutate: updateOrganizationName,
    isError: errorUpdatingOrgName,
    isSuccess: successUpdatingOrgName,
  } = useMutation(
    async ({updatedOrgName}: {updatedOrgName: string}) => {
      return updateOrgName(updatedOrgName);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['superuserorgs']);
      },
    },
  );
  return {
    updateOrganizationName,
    errorUpdatingOrgName,
    successUpdatingOrgName,
  };
}

export function useTakeOwnershipOfOrg({onSuccess, onError}) {
  const queryClient = useQueryClient();

  const changeOrgOwnershipMutator = useMutation(
    async ({orgName}: {orgName: string}) => takeOwnershipOfOrg(orgName),
    {
      onSuccess: () => {
        onSuccess();
        queryClient.invalidateQueries(['superuserusers']);
      },
      onError: (err) => {
        onError(err);
      },
    },
  );

  return {
    changeOrgOwnership: async (orgName: string) =>
      changeOrgOwnershipMutator.mutate({orgName}),
    loadingChangingOwnership: changeOrgOwnershipMutator.isLoading,
    errorChangingOwnership: changeOrgOwnershipMutator.error,
  };
}
