import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useFetchDefaultPermissions,
  useUpdateDefaultPermission,
  useDeleteDefaultPermission,
  useCreateDefaultPermission,
} from './UseDefaultPermissions';
import {
  fetchDefaultPermissions,
  updateDefaultPermission,
  deleteDefaultPermission,
  createDefaultPermission,
} from 'src/resources/DefaultPermissionResource';

vi.mock('src/resources/DefaultPermissionResource', () => ({
  fetchDefaultPermissions: vi.fn(),
  updateDefaultPermission: vi.fn(),
  deleteDefaultPermission: vi.fn(),
  createDefaultPermission: vi.fn(),
  bulkDeleteDefaultPermissions: vi.fn(),
  addRepoPermissionToTeam: vi.fn(),
}));

vi.mock(
  'src/routes/OrganizationsList/Organization/Tabs/DefaultPermissions/DefaultPermissionsList',
  () => ({permissionColumnNames: {repoCreatedBy: 'repoCreatedBy'}}),
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

describe('UseDefaultPermissions', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useFetchDefaultPermissions', () => {
    it('fetches and transforms prototypes to default permissions', async () => {
      vi.mocked(fetchDefaultPermissions).mockResolvedValueOnce([
        {
          activating_user: {name: 'alice'},
          delegate: {name: 'bob'},
          role: 'read',
          id: 'perm-1',
        },
        {
          delegate: {name: 'ci-robot'},
          role: 'write',
          id: 'perm-2',
        },
      ] as any);
      const {result} = renderHook(() => useFetchDefaultPermissions('myorg'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.loading).toBe(false));
      expect(result.current.defaultPermissions).toHaveLength(2);
      expect(result.current.defaultPermissions[0].createdBy).toBe('alice');
      // No activating user → 'organization default'
      expect(result.current.defaultPermissions[1].createdBy).toBe(
        'organization default',
      );
    });
  });

  describe('useUpdateDefaultPermission', () => {
    it('calls updateDefaultPermission on mutate', async () => {
      vi.mocked(updateDefaultPermission).mockResolvedValueOnce(undefined);
      const {result} = renderHook(() => useUpdateDefaultPermission('myorg'), {
        wrapper,
      });
      act(() => {
        result.current.setDefaultPermission({id: 'perm-1', newRole: 'admin'});
      });
      await waitFor(() =>
        expect(result.current.successSetDefaultPermission).toBe(true),
      );
      expect(updateDefaultPermission).toHaveBeenCalledWith(
        'myorg',
        'perm-1',
        'admin',
      );
    });
  });

  describe('useDeleteDefaultPermission', () => {
    it('calls deleteDefaultPermission on mutate', async () => {
      vi.mocked(deleteDefaultPermission).mockResolvedValueOnce(undefined);
      const {result} = renderHook(() => useDeleteDefaultPermission('myorg'), {
        wrapper,
      });
      const mockPerm = {
        createdBy: 'alice',
        appliedTo: 'bob',
        permission: 'read',
        id: 'perm-1',
      };
      act(() => {
        result.current.removeDefaultPermission({perm: mockPerm});
      });
      await waitFor(() =>
        expect(result.current.successDeleteDefaultPermission).toBe(true),
      );
    });
  });

  describe('useCreateDefaultPermission', () => {
    it('calls createDefaultPermission and fires onSuccess', async () => {
      vi.mocked(createDefaultPermission).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useCreateDefaultPermission('myorg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.createDefaultPermission({
          appliedTo: {
            name: 'bob',
            kind: 'user' as any,
            is_robot: false,
            is_org_member: true,
          },
          newRole: 'read',
        });
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    });
  });
});
