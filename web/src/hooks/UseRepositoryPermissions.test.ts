import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useRepositoryPermissions} from './UseRepositoryPermissions';
import {
  fetchAllTeamPermissionsForRepository,
  fetchUserRepoPermissions,
} from 'src/resources/RepositoryResource';
import {EntityKind} from 'src/resources/UserResource';

vi.mock('src/resources/RepositoryResource', () => ({
  fetchAllTeamPermissionsForRepository: vi.fn(),
  fetchUserRepoPermissions: vi.fn(),
}));

vi.mock('src/resources/UserResource', () => ({
  EntityKind: {robot: 'robot', user: 'user', team: 'team'},
}));

vi.mock('src/routes/RepositoryDetails/Settings/ColumnNames', () => ({
  PermissionsColumnNames: {account: 'account'},
}));

/** QueryClientProvider wrapper for hooks that use React Query. */
function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

describe('useRepositoryPermissions', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('assembles members from user and team role responses', async () => {
    vi.mocked(fetchUserRepoPermissions).mockResolvedValueOnce({
      alice: {role: 'read', is_robot: false},
      'myorg+robot1': {role: 'write', is_robot: true},
    } as any);
    vi.mocked(fetchAllTeamPermissionsForRepository).mockResolvedValueOnce({
      myteam: {role: 'admin'},
    } as any);

    const {result} = renderHook(
      () => useRepositoryPermissions('myorg', 'myrepo'),
      {wrapper},
    );
    await waitFor(() => expect(result.current.loading).toBe(false));

    const members = result.current.members;
    expect(members).toHaveLength(3);

    const alice = members.find((m) => m.name === 'alice');
    expect(alice?.type).toBe(EntityKind.user);
    expect(alice?.role).toBe('read');

    const robot = members.find((m) => m.name === 'myorg+robot1');
    expect(robot?.type).toBe(EntityKind.robot);

    const team = members.find((m) => m.name === 'myteam');
    expect(team?.type).toBe(EntityKind.team);
    expect(team?.role).toBe('admin');
  });

  it('returns empty members list when no permissions exist', async () => {
    vi.mocked(fetchUserRepoPermissions).mockResolvedValueOnce({} as any);
    vi.mocked(fetchAllTeamPermissionsForRepository).mockResolvedValueOnce(
      {} as any,
    );

    const {result} = renderHook(
      () => useRepositoryPermissions('myorg', 'myrepo'),
      {wrapper},
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.members).toHaveLength(0);
    expect(result.current.error).toBe(false);
  });

  it('filters members by search query', async () => {
    vi.mocked(fetchUserRepoPermissions).mockResolvedValueOnce({
      alice: {role: 'read', is_robot: false},
      bob: {role: 'write', is_robot: false},
    } as any);
    vi.mocked(fetchAllTeamPermissionsForRepository).mockResolvedValueOnce(
      {} as any,
    );

    const {result} = renderHook(
      () => useRepositoryPermissions('myorg', 'myrepo'),
      {wrapper},
    );
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.setSearch({query: 'ali', field: 'account'});
    });
    expect(result.current.paginatedMembers).toHaveLength(1);
    expect(result.current.paginatedMembers[0].name).toBe('alice');
  });

  it('paginates members correctly', async () => {
    const manyUsers: Record<string, {role: string; is_robot: boolean}> = {};
    for (let i = 0; i < 25; i++) {
      manyUsers[`user${i}`] = {role: 'read', is_robot: false};
    }
    vi.mocked(fetchUserRepoPermissions).mockResolvedValueOnce(manyUsers as any);
    vi.mocked(fetchAllTeamPermissionsForRepository).mockResolvedValueOnce(
      {} as any,
    );

    const {result} = renderHook(
      () => useRepositoryPermissions('myorg', 'myrepo'),
      {wrapper},
    );
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.members).toHaveLength(25);
    expect(result.current.paginatedMembers).toHaveLength(20);

    act(() => {
      result.current.setPage(2);
    });
    expect(result.current.paginatedMembers).toHaveLength(5);
  });
});
