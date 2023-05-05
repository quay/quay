import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {
  bulkDeleteTeams,
  createNewTeamForNamespac,
  fetchTeamRepoPermsForOrg,
  fetchTeamsForNamespace,
  updateTeamRepoPerm,
  updateTeamRoleForNamespace,
} from 'src/resources/TeamResources';
import {useState} from 'react';
import {IAvatar} from 'src/resources/OrganizationResource';
import {teamViewColumnNames} from 'src/routes/OrganizationsList/Organization/Tabs/TeamsAndMembership/TeamsView/TeamsViewList';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {setRepoPermForTeamColumnNames} from 'src/routes/OrganizationsList/Organization/Tabs/TeamsAndMembership/TeamsView/SetRepoPermissionsModal/SetRepoPermissionForTeamModal';
import {
  IRepository,
  fetchRepositoriesForNamespace,
} from 'src/resources/RepositoryResource';
import {BulkOperationError, ResourceError} from 'src/resources/ErrorHandling';
import {useCurrentUser} from './UseCurrentUser';

export function useCreateTeam(ns) {
  const [namespace] = useState(ns);
  const queryClient = useQueryClient();

  const createTeamMutator = useMutation(
    async ({namespace, name, description}: createNewTeamForNamespaceParams) => {
      return createNewTeamForNamespac(namespace, name, description);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['organization', namespace, 'teams']);
      },
    },
  );

  return {
    createNewTeamHook: async (params: createNewTeamForNamespaceParams) =>
      createTeamMutator.mutate(params),
  };
}

interface createNewTeamForNamespaceParams {
  namespace: string;
  name: string;
  description: string;
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
  const [perPage, setPerPage] = useState(10);
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

  const teams: ITeams[] = Object.values(data);

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
    paginatedTeams: paginatedTeams,
    loading: isLoading || isPlaceholderData,
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

export function useFetchRepoPermForTeam(orgName: string, teamName: string) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
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
    ({signal}) => fetchRepositoriesForNamespace(orgName, signal),
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

export function useUpdateTeamRole(orgName: string) {
  const queryClient = useQueryClient();
  const {
    mutate: updateTeamRole,
    isError: errorUpdateTeamRole,
    isSuccess: successUpdateTeamRole,
    reset: resetUpdateTeamRole,
  } = useMutation(
    async ({teamName, teamRole}: {teamName: string; teamRole: string}) => {
      return updateTeamRoleForNamespace(orgName, teamName, teamRole);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['teams']);
      },
    },
  );
  return {
    updateTeamRole,
    errorUpdateTeamRole,
    successUpdateTeamRole,
    resetUpdateTeamRole,
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
