import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useUpdateRepositoryPermissions} from './UseUpdateRepositoryPermissions';
import {
  bulkDeleteRepoPermissions,
  bulkSetRepoPermissions,
} from 'src/resources/RepositoryResource';

vi.mock('src/resources/RepositoryResource', () => ({
  bulkDeleteRepoPermissions: vi.fn(),
  bulkSetRepoPermissions: vi.fn(),
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

describe('useUpdateRepositoryPermissions', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('calls bulkSetRepoPermissions and reports success', async () => {
    vi.mocked(bulkSetRepoPermissions).mockResolvedValueOnce(undefined);
    const {result} = renderHook(
      () => useUpdateRepositoryPermissions('myorg', 'myrepo'),
      {wrapper},
    );
    const members = [
      {org: 'myorg', repo: 'myrepo', name: 'alice', type: 'user', role: 'read'},
    ];
    act(() => {
      result.current.setPermissions({
        members: members as any,
        newRole: 'write' as any,
      });
    });
    await waitFor(() =>
      expect(result.current.successSetPermissions).toBe(true),
    );
    expect(bulkSetRepoPermissions).toHaveBeenCalledWith(members, 'write');
  });

  it('calls bulkDeleteRepoPermissions and reports success', async () => {
    vi.mocked(bulkDeleteRepoPermissions).mockResolvedValueOnce(undefined);
    const {result} = renderHook(
      () => useUpdateRepositoryPermissions('myorg', 'myrepo'),
      {wrapper},
    );
    const members = [
      {org: 'myorg', repo: 'myrepo', name: 'alice', type: 'user', role: 'read'},
    ];
    act(() => {
      result.current.deletePermissions(members as any);
    });
    await waitFor(() =>
      expect(result.current.successDeletePermissions).toBe(true),
    );
    expect(bulkDeleteRepoPermissions).toHaveBeenCalledWith(members);
  });
});
