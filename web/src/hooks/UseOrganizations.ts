import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {useState} from 'react';
import {useRecoilState, useRecoilValue} from 'recoil';
import {
  searchOrgsFilterState,
  searchOrgsState,
} from 'src/atoms/OrganizationListState';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {
  bulkDeleteOrganizations,
  createOrg,
  fetchOrgsAsSuperUser,
} from 'src/resources/OrganizationResource';
import {fetchUsersAsSuperUser} from 'src/resources/UserResource';
import {useCurrentUser} from './UseCurrentUser';

export type OrganizationDetail = {name: string; isUser: boolean};

export function useOrganizations() {
  // Get user and config data
  const {isSuperUser, user, loading, error} = useCurrentUser();

  // Keep state of current search in this hook
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [search, setSearch] = useRecoilState<SearchState>(searchOrgsState);
  const searchFilter = useRecoilValue(searchOrgsFilterState);

  // Get super user orgs
  const {data: superUserOrganizations} = useQuery(
    ['organization', 'superuser', 'organizations'],
    fetchOrgsAsSuperUser,
    {
      enabled: isSuperUser,
    },
  );

  // Get super user users
  const {data: superUserUsers} = useQuery(
    ['organization', 'superuser', 'users'],
    fetchUsersAsSuperUser,
    {
      enabled: isSuperUser,
    },
  );

  // Get org names
  let orgnames: string[];
  if (isSuperUser) {
    orgnames = (superUserOrganizations || []).map((org) => org.name);
  } else {
    orgnames = (user?.organizations || []).map((org) => org.name);
  }
  // Get user names
  let usernames: string[];
  if (isSuperUser) {
    usernames = (superUserUsers || [])
      .map((user) => user.username)
      .filter((x) => x);
  } else {
    usernames = [user.username];
  }

  const organizationsTableDetails = [] as OrganizationDetail[];
  for (const orgname of orgnames) {
    organizationsTableDetails.push({
      name: orgname,
      isUser: false,
    });
  }
  for (const username of usernames) {
    organizationsTableDetails.push({
      name: username,
      isUser: true,
    });
  }

  // Get query client for mutations
  const queryClient = useQueryClient();

  const createOrganizationMutator = useMutation(
    async ({name, email}: {name: string; email: string}) => {
      return createOrg(name, email);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['user']);
      },
    },
  );

  const deleteOrganizationMutator = useMutation(
    async (names: string[]) => {
      return bulkDeleteOrganizations(names, isSuperUser);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['user']);
      },
    },
  );

  return {
    // Data
    superUserOrganizations,
    superUserUsers,
    organizationsTableDetails,

    // Fetching State
    loading,
    error,

    // Search Query State
    search,
    setSearch,
    searchFilter,
    page,
    setPage,
    perPage,
    setPerPage,

    // Useful Metadata
    totalResults: organizationsTableDetails.length,

    // Mutations
    createOrganization: async (name: string, email: string) =>
      createOrganizationMutator.mutate({name, email}),
    deleteOrganizations: async (names: string[]) =>
      deleteOrganizationMutator.mutate(names),
    usernames,
  };
}
