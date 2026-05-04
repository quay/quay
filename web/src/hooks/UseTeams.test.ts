import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useCreateTeam,
  useFetchTeams,
  useDeleteTeam,
  useUpdateTeamDetails,
  useUpdateTeamRepoPerm,
  useAddRepoPermissionToTeam,
} from './UseTeams';
import {
  bulkDeleteTeams,
  createNewTeamForNamespace,
  fetchTeamsForNamespace,
  updateTeamRepoPerm,
  updateTeamDetailsForNamespace,
} from 'src/resources/TeamResources';
import {addRepoPermissionToTeam} from 'src/resources/DefaultPermissionResource';

vi.mock('src/resources/TeamResources', () => ({
  bulkDeleteTeams: vi.fn(),
  createNewTeamForNamespace: vi.fn(),
  fetchTeamRepoPermsForOrg: vi.fn(),
  fetchTeamsForNamespace: vi.fn(),
  updateTeamRepoPerm: vi.fn(),
  updateTeamDetailsForNamespace: vi.fn(),
}));

vi.mock('src/resources/RepositoryResource', () => ({
  fetchRepositoriesForNamespace: vi.fn(),
}));

vi.mock('src/resources/DefaultPermissionResource', () => ({
  addRepoPermissionToTeam: vi.fn(),
}));

vi.mock('src/resources/ErrorHandling', () => ({
  BulkOperationError: class BulkOperationError extends Error {},
  ResourceError: class ResourceError extends Error {},
}));

vi.mock('./UseCurrentUser', () => ({
  useCurrentUser: vi.fn(() => ({user: {username: 'testuser'}})),
}));

vi.mock('src/contexts/UIContext', () => ({
  useUI: vi.fn(() => ({addAlert: vi.fn()})),
  AlertVariant: {Failure: 'danger', Success: 'success'},
}));

vi.mock(
  'src/routes/OrganizationsList/Organization/Tabs/TeamsAndMembership/TeamsView/TeamsViewList',
  () => ({teamViewColumnNames: {teamName: 'Team name'}}),
);

vi.mock(
  'src/routes/OrganizationsList/Organization/Tabs/TeamsAndMembership/TeamsView/SetRepoPermissionsModal/SetRepoPermissionForTeamModal',
  () => ({setRepoPermForTeamColumnNames: {repoName: 'Repository name'}}),
);

function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

describe('UseTeams', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useCreateTeam', () => {
    it('calls createNewTeamForNamespace and fires onSuccess for new team', async () => {
      vi.mocked(createNewTeamForNamespace).mockResolvedValueOnce({
        new_team: true,
        name: 'newteam',
      });
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useCreateTeam('myorg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.createNewTeamHook({
          teamName: 'newteam',
          description: 'A new team',
        });
      });
      await waitFor(() => expect(result.current.successCreateTeam).toBe(true));
      expect(createNewTeamForNamespace).toHaveBeenCalledWith(
        'myorg',
        'newteam',
        'A new team',
      );
      expect(onSuccess).toHaveBeenCalled();
    });

    it('fires onError when creation fails', async () => {
      vi.mocked(createNewTeamForNamespace).mockRejectedValueOnce(
        new Error('fail'),
      );
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useCreateTeam('myorg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.createNewTeamHook({
          teamName: 'newteam',
          description: 'desc',
        });
      });
      await waitFor(() => expect(result.current.errorCreateTeam).toBe(true));
      expect(onError).toHaveBeenCalled();
    });
  });

  describe('useFetchTeams', () => {
    it('fetches teams and returns paginated list', async () => {
      const mockTeams = [
        {
          name: 'alpha',
          description: '',
          role: 'member',
          can_view: true,
          repo_count: 0,
          member_count: 1,
          is_synced: false,
        },
        {
          name: 'beta',
          description: '',
          role: 'admin',
          can_view: true,
          repo_count: 2,
          member_count: 3,
          is_synced: false,
        },
      ];
      vi.mocked(fetchTeamsForNamespace).mockResolvedValueOnce(mockTeams as any);
      const {result} = renderHook(() => useFetchTeams('myorg'), {wrapper});
      await waitFor(() => expect(result.current.isLoadingTeams).toBe(false));
      expect(result.current.teams).toHaveLength(2);
      expect(result.current.paginatedTeams).toHaveLength(2);
    });

    it('filters teams by search query', async () => {
      const mockTeams = [
        {
          name: 'alpha',
          description: '',
          role: 'member',
          can_view: true,
          repo_count: 0,
          member_count: 1,
          is_synced: false,
        },
        {
          name: 'beta',
          description: '',
          role: 'admin',
          can_view: true,
          repo_count: 2,
          member_count: 3,
          is_synced: false,
        },
      ];
      vi.mocked(fetchTeamsForNamespace).mockResolvedValueOnce(mockTeams as any);
      const {result} = renderHook(() => useFetchTeams('myorg'), {wrapper});
      await waitFor(() => expect(result.current.isLoadingTeams).toBe(false));
      act(() => {
        result.current.setSearch({query: 'alpha', field: 'Team name'});
      });
      expect(result.current.filteredTeams).toHaveLength(1);
      expect(result.current.filteredTeams[0].name).toBe('alpha');
    });
  });

  describe('useDeleteTeam', () => {
    it('calls bulkDeleteTeams and fires onSuccess', async () => {
      vi.mocked(bulkDeleteTeams).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useDeleteTeam({orgName: 'myorg', onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.removeTeam({name: 'alpha'} as any);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(bulkDeleteTeams).toHaveBeenCalledWith('myorg', [{name: 'alpha'}]);
    });

    it('calls onError when deletion fails', async () => {
      vi.mocked(bulkDeleteTeams).mockRejectedValueOnce(new Error('fail'));
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useDeleteTeam({orgName: 'myorg', onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.removeTeam([{name: 'alpha'}] as any);
      });
      await waitFor(() => expect(onError).toHaveBeenCalled());
    });
  });

  describe('useUpdateTeamDetails', () => {
    it('calls updateTeamDetailsForNamespace on mutate', async () => {
      vi.mocked(updateTeamDetailsForNamespace).mockResolvedValueOnce(undefined);
      const {result} = renderHook(() => useUpdateTeamDetails('myorg'), {
        wrapper,
      });
      act(() => {
        result.current.updateTeamDetails({
          teamName: 'alpha',
          teamRole: 'admin',
          teamDescription: 'Updated',
        });
      });
      await waitFor(() =>
        expect(result.current.successUpdateTeamDetails).toBe(true),
      );
      expect(updateTeamDetailsForNamespace).toHaveBeenCalledWith(
        'myorg',
        'alpha',
        'admin',
        'Updated',
      );
    });
  });

  describe('useUpdateTeamRepoPerm', () => {
    it('calls updateTeamRepoPerm on mutate', async () => {
      vi.mocked(updateTeamRepoPerm).mockResolvedValueOnce(undefined);
      const {result} = renderHook(
        () => useUpdateTeamRepoPerm('myorg', 'alpha'),
        {wrapper},
      );
      const perms = [{repoName: 'repo1', role: 'read', lastModified: 0}];
      act(() => {
        result.current.updateRepoPerm({teamRepoPerms: perms});
      });
      await waitFor(() =>
        expect(result.current.successUpdateRepoPerm).toBe(true),
      );
      expect(updateTeamRepoPerm).toHaveBeenCalledWith('myorg', 'alpha', perms);
    });

    it('exposes error state on failure', async () => {
      vi.mocked(updateTeamRepoPerm).mockRejectedValueOnce(new Error('fail'));
      const {result} = renderHook(
        () => useUpdateTeamRepoPerm('myorg', 'alpha'),
        {wrapper},
      );
      act(() => {
        result.current.updateRepoPerm({
          teamRepoPerms: [{repoName: 'r', role: 'w', lastModified: 0}],
        });
      });
      await waitFor(() =>
        expect(result.current.errorUpdateRepoPerm).toBe(true),
      );
    });
  });

  describe('useAddRepoPermissionToTeam', () => {
    it('calls addRepoPermissionToTeam on mutate', async () => {
      vi.mocked(addRepoPermissionToTeam).mockResolvedValueOnce(undefined);
      const {result} = renderHook(
        () => useAddRepoPermissionToTeam('myorg', 'alpha'),
        {wrapper},
      );
      act(() => {
        result.current.addRepoPermToTeam({
          repoName: 'myrepo',
          newRole: 'write',
        });
      });
      await waitFor(() =>
        expect(result.current.successAddingRepoPermissionToTeam).toBe(true),
      );
      expect(addRepoPermissionToTeam).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        'alpha',
        'write',
      );
    });
  });
});
