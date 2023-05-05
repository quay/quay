import {useQuery} from '@tanstack/react-query';
import {useState} from 'react';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {
  fetchAllTeamPermissionsForRepository,
  fetchUserRepoPermissions,
  RepoMember,
} from 'src/resources/RepositoryResource';
import {PermissionsColumnNames} from 'src/routes/RepositoryDetails/Settings/ColumnNames';

enum MemberType {
  user = 'user',
  robot = 'robot',
  team = 'team',
}

export function useRepositoryPermissions(org: string, repo: string) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [search, setSearch] = useState<SearchState>({
    query: '',
    field: PermissionsColumnNames.account,
  });

  const {
    data: userRoles,
    isError: errorLoadingUserRoles,
    isLoading: loadingUserRoles,
    isPlaceholderData: isUserPlaceholderData,
  } = useQuery(
    ['userrepopermissions', org, repo],
    () => fetchUserRepoPermissions(org, repo),
    {
      placeholderData: {},
    },
  );

  const {
    data: teamRoles,
    isError: errorLoadingTeamRoles,
    isLoading: loadingTeamRoles,
    isPlaceholderData: isTeamPlaceholderData,
  } = useQuery(
    ['teamrepopermissions', org, repo],
    () => fetchAllTeamPermissionsForRepository(org, repo),
    {
      placeholderData: {},
    },
  );

  const members: RepoMember[] = [];
  for (const [name, roleData] of Object.entries(userRoles)) {
    const type: MemberType = roleData.is_robot
      ? MemberType.robot
      : MemberType.user;
    members.push({
      org: org,
      repo: repo,
      name: name,
      type: type,
      role: roleData.role,
    });
  }
  for (const [name, roleData] of Object.entries(teamRoles)) {
    members.push({
      org: org,
      repo: repo,
      name: name,
      type: MemberType.team,
      role: roleData.role,
    });
  }

  const filteredMembers =
    search.query !== ''
      ? members?.filter((role) => role.name.includes(search.query))
      : members;

  const paginatedMembers = filteredMembers?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  return {
    loading:
      loadingUserRoles ||
      loadingTeamRoles ||
      isUserPlaceholderData ||
      isTeamPlaceholderData,
    error: errorLoadingUserRoles || errorLoadingTeamRoles,
    members: members,
    paginatedMembers: paginatedMembers,

    page: page,
    setPage: setPage,
    perPage: perPage,
    setPerPage: setPerPage,

    search: search,
    setSearch: setSearch,
  };
}
