import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {useMemo, useState} from 'react';
import {useRecoilState, useRecoilValue} from 'recoil';
import {
  searchOrgsFilterState,
  searchOrgsState,
} from 'src/atoms/OrganizationListState';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {IQuotaReport} from 'src/libs/quotaUtils';
import {
  bulkDeleteOrganizations,
  createOrg,
  fetchOrgsAsSuperUser,
  IAvatar,
} from 'src/resources/OrganizationResource';
import {
  fetchUsersAsSuperUser,
  deleteSuperuserUser,
} from 'src/resources/UserResource';
import {BulkOperationError} from 'src/resources/ErrorHandling';
import {useCurrentUser} from './UseCurrentUser';
import {useSuperuserPermissions} from './UseSuperuserPermissions';

export type OrganizationDetail = {
  name: string;
  isUser: boolean;
  userEnabled?: boolean;
  userSuperuser?: boolean;
  quota_report?: IQuotaReport;
  avatar?: IAvatar;
};

export function useOrganizations() {
  // Get user and config data
  const {isSuperUser, user, loading, error} = useCurrentUser();
  const {canModify} = useSuperuserPermissions();

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
      retry: false,
      enabled: isSuperUser === true && !loading,
    },
  );

  // Get super user users
  const {data: superUserUsers} = useQuery(
    ['organization', 'superuser', 'users'],
    fetchUsersAsSuperUser,
    {
      retry: false,
      enabled: isSuperUser === true && !loading,
    },
  );

  const organizationsTableDetails = useMemo(() => {
    // Build org names list: always include user's orgs, add superuser orgs if available
    const userOrgNames = (user?.organizations || []).map((org) => org.name);
    let orgnames: string[] = [...userOrgNames];

    if (isSuperUser && superUserOrganizations) {
      const superOrgNames = superUserOrganizations.map((org) => org.name);
      const additionalOrgNames = superOrgNames.filter(
        (name) => !userOrgNames.includes(name),
      );
      orgnames = [...orgnames, ...additionalOrgNames];
    }

    // Build user names list: always include current user, add superuser users if available
    const currentUsername = user?.username ? [user.username] : [];
    let usernames: string[] = [...currentUsername];

    if (isSuperUser && superUserUsers) {
      const superUsernames = superUserUsers
        .map((user) => user.username)
        .filter((x) => x);
      const additionalUsernames = superUsernames.filter(
        (name) => !currentUsername.includes(name),
      );
      usernames = [...usernames, ...additionalUsernames];
    }

    const details = [] as OrganizationDetail[];
    for (const orgname of orgnames) {
      const orgObj = (superUserOrganizations || []).find(
        (o) => o.name === orgname,
      );
      details.push({
        name: orgname,
        isUser: false,
        quota_report: orgObj?.quota_report,
        avatar: orgObj?.avatar,
      });
    }
    for (const username of usernames) {
      const userObj = (superUserUsers || []).find(
        (u) => u.username === username,
      );
      details.push({
        name: username,
        isUser: true,
        userEnabled: userObj?.enabled,
        userSuperuser: userObj?.super_user,
        quota_report: userObj?.quota_report,
        avatar: userObj?.avatar,
      });
    }

    return details;
  }, [user, isSuperUser, superUserOrganizations, superUserUsers]);

  const userEmailMap = useMemo(() => {
    const emailMap: Record<string, string> = {};
    if (isSuperUser && superUserUsers) {
      superUserUsers.forEach((user) => {
        if (user.username && user.email) {
          emailMap[user.username] = user.email;
        }
      });
    }
    return emailMap;
  }, [isSuperUser, superUserUsers]);

  const usernames = useMemo(() => {
    const currentUsername = user?.username ? [user.username] : [];
    let usernamesList: string[] = [...currentUsername];

    if (isSuperUser && superUserUsers) {
      const superUsernames = superUserUsers
        .map((user) => user.username)
        .filter((x) => x);
      const additionalUsernames = superUsernames.filter(
        (name) => !currentUsername.includes(name),
      );
      usernamesList = [...usernamesList, ...additionalUsernames];
    }

    return usernamesList;
  }, [user, isSuperUser, superUserUsers]);

  // Get query client for mutations
  const queryClient = useQueryClient();

  const createOrganizationMutator = useMutation(
    async ({name, email}: {name: string; email: string}) => {
      return createOrg(name, email);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['user']);
        queryClient.invalidateQueries([
          'organization',
          'superuser',
          'organizations',
        ]);
        queryClient.invalidateQueries(['organization', 'superuser', 'users']);
      },
    },
  );

  const deleteOrganizationMutator = useMutation(
    async (names: string[]) => {
      // Use canModify instead of isSuperUser to prevent read-only superusers from deleting
      return bulkDeleteOrganizations(names, canModify);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['user']);
        queryClient.invalidateQueries([
          'organization',
          'superuser',
          'organizations',
        ]);
        queryClient.invalidateQueries(['organization', 'superuser', 'users']);
      },
    },
  );

  const deleteUsersMutator = useMutation(
    async (usernames: string[]) => {
      const responses = await Promise.allSettled(
        usernames.map((username) =>
          deleteSuperuserUser(username).catch((err) => {
            throw Object.assign(err, {username});
          }),
        ),
      );

      // Aggregate failed responses
      const errResponses = responses.filter(
        (r) => r.status === 'rejected',
      ) as PromiseRejectedResult[];

      // If errors, collect and throw
      if (errResponses.length > 0) {
        const bulkDeleteError = new BulkOperationError('error deleting users');
        for (const response of errResponses) {
          const reason = response.reason;
          bulkDeleteError.addError(reason.username || 'unknown', reason);
        }
        throw bulkDeleteError;
      }

      return responses;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['user']);
        queryClient.invalidateQueries([
          'organization',
          'superuser',
          'organizations',
        ]);
        queryClient.invalidateQueries(['organization', 'superuser', 'users']);
      },
    },
  );

  return {
    // Data
    superUserOrganizations,
    superUserUsers,
    organizationsTableDetails,
    userEmailMap,

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
      deleteOrganizationMutator.mutateAsync(names),
    deleteUsers: async (usernames: string[]) =>
      deleteUsersMutator.mutateAsync(usernames),
    usernames,
  };
}
