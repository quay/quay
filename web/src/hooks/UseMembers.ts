import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {useState} from 'react';
import {SearchState} from 'src/components/toolbar/SearchTypes';
import {
  IMemberTeams,
  IMembers,
  deleteCollaboratorForOrg,
  deleteTeamMemberForOrg,
  fetchCollaboratorsForOrg,
  fetchMembersForOrg,
  fetchTeamMembersForOrg,
} from 'src/resources/MembersResource';
import {IAvatar} from 'src/resources/OrganizationResource';
import {collaboratorViewColumnNames} from 'src/routes/OrganizationsList/Organization/Tabs/TeamsAndMembership/CollaboratorsView/CollaboratorsViewList';
import {memberViewColumnNames} from 'src/routes/OrganizationsList/Organization/Tabs/TeamsAndMembership/MembersView/MembersViewList';
import {manageMemberColumnNames} from 'src/routes/OrganizationsList/Organization/Tabs/TeamsAndMembership/TeamsView/ManageMembers/ManageMembersList';

export function useFetchMembers(orgName: string) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [search, setSearch] = useState<SearchState>({
    query: '',
    field: memberViewColumnNames.username,
  });

  const {
    data: members,
    isLoading,
    isPlaceholderData,
    isError: errorLoadingMembers,
  } = useQuery<IMembers[]>(
    ['members'],
    ({signal}) => fetchMembersForOrg(orgName, signal),
    {
      placeholderData: [],
    },
  );

  const filteredMembers =
    search.query !== ''
      ? members?.filter((member) => member.name.includes(search.query))
      : members;

  const paginatedMembers = filteredMembers?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  return {
    members,
    filteredMembers,
    paginatedMembers: paginatedMembers,
    loading: isLoading || isPlaceholderData,
    error: errorLoadingMembers,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  };
}

export interface ITeamMember {
  name: string;
  kind: string;
  is_robot: false;
  avatar: IAvatar;
  invited: boolean;
}

export function useFetchTeamMembersForOrg(orgName: string, teamName: string) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [search, setSearch] = useState<SearchState>({
    query: '',
    field: manageMemberColumnNames.teamMember,
  });

  const {
    data,
    isLoading,
    isPlaceholderData,
    isError: errorLoadingTeamMembers,
  } = useQuery<ITeamMember[]>(
    ['teamMembers'],
    ({signal}) => fetchTeamMembersForOrg(orgName, teamName, signal),
    {
      placeholderData: [],
    },
  );

  const allMembers: ITeamMember[] = data;
  const filteredAllMembers =
    search.query !== ''
      ? allMembers?.filter((member) => member.name.includes(search.query))
      : allMembers;
  const paginatedAllMembers = filteredAllMembers?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  // Filter team members
  const teamMembers = allMembers?.filter(
    (team) => !team.is_robot && !team.invited,
  );
  const filteredTeamMembers =
    search.query !== ''
      ? teamMembers?.filter((member) => member.name.includes(search.query))
      : teamMembers;
  const paginatedTeamMembers = filteredTeamMembers?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  // Filter robot account
  const robotAccounts = allMembers?.filter((team) => team.is_robot);
  const filteredRobotAccounts =
    search.query !== ''
      ? robotAccounts?.filter((member) => member.name.includes(search.query))
      : robotAccounts;
  const paginatedRobotAccounts = filteredRobotAccounts?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  // Filter invited members
  const invited = allMembers?.filter((team) => team.invited);
  const filteredInvited =
    search.query !== ''
      ? invited?.filter((member) => member.name.includes(search.query))
      : invited;
  const paginatedInvited = filteredInvited?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  return {
    allMembers,
    teamMembers,
    robotAccounts,
    invited,
    paginatedAllMembers,
    paginatedTeamMembers,
    paginatedRobotAccounts,
    paginatedInvited,
    loading: isLoading || isPlaceholderData,
    error: errorLoadingTeamMembers,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  };
}

export function useFetchCollaborators(orgName: string) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [search, setSearch] = useState<SearchState>({
    query: '',
    field: collaboratorViewColumnNames.username,
  });

  const {
    data: collaborators,
    isLoading,
    isPlaceholderData,
    isError: errorLoadingCollaborators,
  } = useQuery<IMembers[]>(
    ['collaborators'],
    ({signal}) => fetchCollaboratorsForOrg(orgName, signal),
    {
      placeholderData: [],
    },
  );

  const filteredCollaborators =
    search.query !== ''
      ? collaborators?.filter((collaborator) =>
          collaborator.name.includes(search.query),
        )
      : collaborators;

  const paginatedCollaborators = filteredCollaborators?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  return {
    collaborators,
    filteredCollaborators,
    paginatedCollaborators,
    loading: isLoading || isPlaceholderData,
    error: errorLoadingCollaborators,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  };
}

export function useDeleteTeamMember(orgName: string) {
  const queryClient = useQueryClient();
  const {
    mutate: removeTeamMember,
    isError: errorDeleteTeamMember,
    isSuccess: successDeleteTeamMember,
    reset: resetDeleteTeamMember,
  } = useMutation(
    async ({teamName, memberName}: {teamName: string; memberName: string}) => {
      return deleteTeamMemberForOrg(orgName, teamName, memberName);
    },
    {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries(['teamMembers']);
      },
    },
  );
  return {
    removeTeamMember,
    errorDeleteTeamMember,
    successDeleteTeamMember,
    resetDeleteTeamMember,
  };
}

export function useDeleteCollaborator(orgName: string) {
  const queryClient = useQueryClient();
  const {
    mutate: removeCollaborator,
    isError: errorDeleteCollaborator,
    isSuccess: successDeleteCollaborator,
    reset: resetDeleteCollaborator,
  } = useMutation(
    async ({collaborator}: {collaborator: string}) => {
      return deleteCollaboratorForOrg(orgName, collaborator);
    },
    {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries(['collaborators']);
      },
    },
  );
  return {
    removeCollaborator,
    errorDeleteCollaborator,
    successDeleteCollaborator,
    resetDeleteCollaborator,
  };
}
