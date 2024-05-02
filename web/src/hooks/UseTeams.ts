import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  bulkDeleteTeams,
  createNewTeamForNamespace,
  fetchTeamRepoPermsForOrg,
  fetchTeamsForNamespace,
  updateTeamRepoPerm,
  updateTeamDetailsForNamespace,
} from 'src/resources/TeamResources';
import {useState} from 'react';
import {teamViewColumnNames} from 'src/routes/OrganizationsList/Organization/Tabs/TeamsAndMembership/TeamsView/TeamsViewList';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {setRepoPermForTeamColumnNames} from 'src/routes/OrganizationsList/Organization/Tabs/TeamsAndMembership/TeamsView/SetRepoPermissionsModal/SetRepoPermissionForTeamModal';
import {
  IRepository,
  fetchRepositoriesForNamespace,
} from 'src/resources/RepositoryResource';
import {BulkOperationError, ResourceError} from 'src/resources/ErrorHandling';
import {useCurrentUser} from './UseCurrentUser';
import {IAvatar} from 'src/resources/OrganizationResource';
import {useAlerts} from './UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {addRepoPermissionToTeam} from 'src/resources/DefaultPermissionResource';

interface createNewTeamForNamespaceParams {
  teamName: string;
  description: string;
}

export function useCreateTeam(orgName, {onSuccess, onError}) {
  const queryClient = useQueryClient();
  const {addAlert} = useAlerts();

  const {
    data: responseData,
    mutate: createNewTeamHook,
    isError: errorCreateTeam,
    isSuccess: successCreateTeam,
  } = useMutation(
    async ({teamName, description}: createNewTeamForNamespaceParams) => {
      return createNewTeamForNamespace(orgName, teamName, description);
    },
    {
      onSuccess: (data) => {
        if (data.new_team) {
          onSuccess();
          queryClient.invalidateQueries(['organization', orgName, 'teams']);
          queryClient.invalidateQueries(['teams']);
        } else {
          addAlert({
            variant: AlertVariant.Failure,
            title: `Team "${data.name}" already exists`,
          });
        }
      },
      onError: () => {
        onError();
      },
    },
  );

  return {
    responseData,
    createNewTeamHook,
    errorCreateTeam,
    successCreateTeam,
  };
}

export interface ITeams {
  name: string;
  description: string;
  role: string;
  avatar: IAvatar;
  can_view: boolean;
  repo_count: number;
  member_count: number;
  is_synced: boolean;
}

export function useFetchTeams(orgName: string) {
  const {user} = useCurrentUser();
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [search, setSearch] = useState<SearchState>({
    query: '',
    field: teamViewColumnNames.teamName,
  });

  const {
    data,
    isLoading,
    isPlaceholderData,
    isError: errorLoadingTeams,
  } = useQuery<ITeams[]>(
    ['teams'],
    ({signal}) => fetchTeamsForNamespace(orgName, signal),
    {
      placeholderData: [],
      enabled: !(user.username === orgName),
    },
  );

  const teams: ITeams[] = data ? Object.values(data) : [];

  const filteredTeams =
    search.query !== ''
      ? teams?.filter((team) => team.name.includes(search.query))
      : teams;

  const paginatedTeams = filteredTeams?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  return {
    teams: teams,
    filteredTeams,
    paginatedTeams,
    isLoadingTeams: isLoading || isPlaceholderData,
    error: errorLoadingTeams,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  };
}

export interface ITeamRepoPerms {
  repoName: string;
  role?: string;
  lastModified: number;
}

export function useFetchRepoPermForTeam(
  orgName: string,
  teamName: string,
  repoKind: string,
) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(20);
  const [search, setSearch] = useState<SearchState>({
    query: '',
    field: setRepoPermForTeamColumnNames.repoName,
  });

  const {
    data: permissions,
    isLoading: loadingPerms,
    isPlaceholderData,
    isError: errorLoadingTeamPerms,
  } = useQuery(
    ['teamrepopermissions'],
    ({signal}) => fetchTeamRepoPermsForOrg(orgName, teamName, signal),
    {
      placeholderData: [],
    },
  );

  const {
    data: repos,
    isLoading: loadingRepos,
    isError: errorLoadingRepos,
  } = useQuery<IRepository[]>(
    ['repos'],
    ({signal}) => fetchRepositoriesForNamespace(orgName, repoKind, signal),
    {
      placeholderData: [],
    },
  );

  const teamRepoPerms: ITeamRepoPerms[] = repos.map((repo) => ({
    repoName: repo.name,
    lastModified: repo.last_modified ? repo.last_modified : -1,
  }));

  // Add role from fetch permissions API
  teamRepoPerms.forEach((repo) => {
    const matchingPerm = permissions?.find(
      (perm) => perm.repository.name === repo.repoName,
    );
    if (matchingPerm) {
      repo['role'] = matchingPerm.role;
    } else {
      repo['role'] = 'none';
    }
  });

  const filteredTeamRepoPerms =
    search.query !== ''
      ? teamRepoPerms?.filter((teamRepoPerm) =>
          teamRepoPerm.repoName.includes(search.query),
        )
      : teamRepoPerms;

  const paginatedTeamRepoPerms = filteredTeamRepoPerms?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  return {
    teamRepoPerms: teamRepoPerms,
    filteredTeamRepoPerms: filteredTeamRepoPerms,
    paginatedTeamRepoPerms: paginatedTeamRepoPerms,
    loading: loadingPerms || loadingRepos || isPlaceholderData,
    error: errorLoadingTeamPerms || errorLoadingRepos,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  };
}

export function useDeleteTeam({orgName, onSuccess, onError}) {
  const queryClient = useQueryClient();
  const deleteTeamsMutator = useMutation(
    async (teams: ITeams[] | ITeams) => {
      teams = Array.isArray(teams) ? teams : [teams];
      return bulkDeleteTeams(orgName, teams);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['teams']);
        onSuccess();
      },
      onError: (err) => {
        onError(err);
      },
    },
  );
  return {
    removeTeam: async (teams: ITeams[] | ITeams) =>
      deleteTeamsMutator.mutate(teams),
  };
}

export function useUpdateTeamDetails(orgName: string) {
  const queryClient = useQueryClient();
  const {
    mutate: updateTeamDetails,
    isError: errorUpdateTeamDetails,
    isSuccess: successUpdateTeamDetails,
  } = useMutation(
    async ({
      teamName,
      teamRole,
      teamDescription,
    }: {
      teamName: string;
      teamRole: string;
      teamDescription?: string;
    }) => {
      return updateTeamDetailsForNamespace(
        orgName,
        teamName,
        teamRole,
        teamDescription,
      );
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['teams']);
      },
    },
  );
  return {
    updateTeamDetails,
    errorUpdateTeamDetails,
    successUpdateTeamDetails,
  };
}

export function useUpdateTeamRepoPerm(orgName: string, teamName: string) {
  const queryClient = useQueryClient();
  const {
    mutate: updateRepoPerm,
    isError: errorUpdateRepoPerm,
    error: detailedErrorUpdateRepoPerm,
    isSuccess: successUpdateRepoPerm,
    reset: resetUpdateRepoPerm,
  } = useMutation(
    async ({teamRepoPerms}: {teamRepoPerms: ITeamRepoPerms[]}) => {
      return updateTeamRepoPerm(orgName, teamName, teamRepoPerms);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['teams']);
      },
    },
  );
  return {
    updateRepoPerm,
    errorUpdateRepoPerm,
    detailedErrorUpdateRepoPerm:
      detailedErrorUpdateRepoPerm as BulkOperationError<ResourceError>,
    successUpdateRepoPerm,
    resetUpdateRepoPerm,
  };
}

export function useAddRepoPermissionToTeam(orgName: string, teamName: string) {
  const queryClient = useQueryClient();
  const {
    mutate: addRepoPermToTeam,
    isError: errorAddingRepoPermissionToTeam,
    isSuccess: successAddingRepoPermissionToTeam,
  } = useMutation(
    async ({repoName, newRole}: {repoName: string; newRole: string}) => {
      return addRepoPermissionToTeam(orgName, repoName, teamName, newRole);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['teams']);
        queryClient.invalidateQueries(['teamrepopermissions']);
      },
    },
  );
  return {
    addRepoPermToTeam,
    errorAddingRepoPermissionToTeam,
    successAddingRepoPermissionToTeam,
  };
}
