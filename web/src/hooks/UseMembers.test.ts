import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useAddMembersToTeam,
  useFetchMembers,
  useFetchCollaborators,
  useDeleteTeamMember,
  useDeleteCollaborator,
} from './UseMembers';
import {
  addMemberToTeamForOrg,
  fetchMembersForOrg,
  fetchCollaboratorsForOrg,
  deleteTeamMemberForOrg,
  deleteCollaboratorForOrg,
} from 'src/resources/MembersResource';

vi.mock('src/resources/MembersResource', () => ({
  addMemberToTeamForOrg: vi.fn(),
  deleteCollaboratorForOrg: vi.fn(),
  deleteTeamMemberForOrg: vi.fn(),
  fetchCollaboratorsForOrg: vi.fn(),
  fetchMembersForOrg: vi.fn(),
  fetchTeamMembersForOrg: vi.fn(),
}));

vi.mock(
  'src/routes/OrganizationsList/Organization/Tabs/TeamsAndMembership/CollaboratorsView/CollaboratorsViewList',
  () => ({collaboratorViewColumnNames: {username: 'username'}}),
);

vi.mock(
  'src/routes/OrganizationsList/Organization/Tabs/TeamsAndMembership/MembersView/MembersViewList',
  () => ({memberViewColumnNames: {username: 'username'}}),
);

vi.mock(
  'src/routes/OrganizationsList/Organization/Tabs/TeamsAndMembership/TeamsView/ManageMembers/ManageMembersList',
  () => ({manageMemberColumnNames: {teamMember: 'teamMember'}}),
);

/** QueryClientProvider wrapper for hooks that use React Query. */
function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

describe('UseMembers', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useAddMembersToTeam', () => {
    it('calls addMemberToTeamForOrg and fires onSuccess', async () => {
      vi.mocked(addMemberToTeamForOrg).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useAddMembersToTeam('myorg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.addMemberToTeam({team: 'myteam', member: 'alice'});
      });
      await waitFor(() =>
        expect(result.current.successAddingMemberToTeam).toBe(true),
      );
      expect(addMemberToTeamForOrg).toHaveBeenCalledWith(
        'myorg',
        'myteam',
        'alice',
      );
    });
  });

  describe('useFetchMembers', () => {
    it('fetches members and returns paginated list', async () => {
      const mockMembers = [
        {name: 'alice', kind: 'user'},
        {name: 'bob', kind: 'user'},
      ];
      vi.mocked(fetchMembersForOrg).mockResolvedValueOnce(mockMembers as any);
      const {result} = renderHook(() => useFetchMembers('myorg'), {wrapper});
      await waitFor(() => expect(result.current.loading).toBe(false));
      expect(result.current.members).toEqual(mockMembers);
      expect(result.current.filteredMembers).toHaveLength(2);
    });

    it('filters members by search query', async () => {
      const mockMembers = [
        {name: 'alice', kind: 'user'},
        {name: 'bob', kind: 'user'},
      ];
      vi.mocked(fetchMembersForOrg).mockResolvedValueOnce(mockMembers as any);
      const {result} = renderHook(() => useFetchMembers('myorg'), {wrapper});
      await waitFor(() => expect(result.current.loading).toBe(false));
      act(() => {
        result.current.setSearch({query: 'ali', field: 'username'});
      });
      await waitFor(() => {
        expect(result.current.filteredMembers).toHaveLength(1);
      });
      expect(result.current.filteredMembers[0].name).toBe('alice');
    });
  });

  describe('useFetchCollaborators', () => {
    it('fetches collaborators and returns them', async () => {
      const mockCollaborators = [{name: 'extuser', kind: 'user'}];
      vi.mocked(fetchCollaboratorsForOrg).mockResolvedValueOnce(
        mockCollaborators as any,
      );
      const {result} = renderHook(() => useFetchCollaborators('myorg'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.loading).toBe(false));
      expect(result.current.collaborators).toEqual(mockCollaborators);
    });
  });

  describe('useDeleteTeamMember', () => {
    it('calls deleteTeamMemberForOrg on mutate', async () => {
      vi.mocked(deleteTeamMemberForOrg).mockResolvedValueOnce(undefined);
      const {result} = renderHook(() => useDeleteTeamMember('myorg'), {
        wrapper,
      });
      act(() => {
        result.current.removeTeamMember({
          teamName: 'myteam',
          memberName: 'alice',
        });
      });
      await waitFor(() =>
        expect(result.current.successDeleteTeamMember).toBe(true),
      );
      expect(deleteTeamMemberForOrg).toHaveBeenCalledWith(
        'myorg',
        'myteam',
        'alice',
      );
    });
  });

  describe('useDeleteCollaborator', () => {
    it('calls deleteCollaboratorForOrg on mutate', async () => {
      vi.mocked(deleteCollaboratorForOrg).mockResolvedValueOnce(undefined);
      const {result} = renderHook(() => useDeleteCollaborator('myorg'), {
        wrapper,
      });
      act(() => {
        result.current.removeCollaborator({collaborator: 'extuser'});
      });
      await waitFor(() =>
        expect(result.current.successDeleteCollaborator).toBe(true),
      );
      expect(deleteCollaboratorForOrg).toHaveBeenCalledWith('myorg', 'extuser');
    });
  });
});
