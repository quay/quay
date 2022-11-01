import {fetchUsersAsSuperUser} from 'src/resources/UserResource';
import {
  bulkDeleteOrganizations,
  fetchOrgsAsSuperUser,
} from 'src/resources/OrganizationResource';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {useCurrentUser} from './UseCurrentUser';
import {createOrg} from 'src/resources/OrganizationResource';

export function useOrganizations() {
  // Get user and config data
  const {isSuperUser, user, loading, error} = useCurrentUser();

  // Get super user orgs
  const {data: superUserOrganizations} = useQuery(
    ['organization', 'superuser'],
    fetchOrgsAsSuperUser,
    {
      enabled: isSuperUser,
    },
  );

  // Get super user users
  const {data: superUserUsers} = useQuery(
    ['organization', 'superuser'],
    fetchUsersAsSuperUser,
    {
      enabled: isSuperUser,
    },
  );

  // Get org names
  let orgnames: string[];
  if (isSuperUser) {
    orgnames = superUserOrganizations.map((org) => org.name);
  } else {
    orgnames = user?.organizations.map((org) => org.name);
  }
  // Get user names
  let usernames: string[];
  if (isSuperUser) {
    usernames = superUserUsers.map((user) => user.username);
  } else {
    usernames = [user.username];
  }

  const organizationsTableDetails = [] as {name: string; isUser: boolean}[];
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
    superUserOrganizations,
    superUserUsers,
    organizationsTableDetails,
    loading,
    error,
    createOrganization: async (name: string, email: string) =>
      createOrganizationMutator.mutate({name, email}),
    deleteOrganizations: async (names: string[]) =>
      deleteOrganizationMutator.mutate(names),
    usernames,
  };
}
