import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useCurrentUser, useUpdateUser, useChangeEmail} from './UseCurrentUser';
import {fetchUser, updateUser} from 'src/resources/UserResource';

vi.mock('src/resources/UserResource', () => ({
  fetchUser: vi.fn(),
  updateUser: vi.fn(),
}));

vi.mock('./UseQuayConfig', () => ({
  useQuayConfig: vi.fn(() => ({
    features: {SUPERUSERS_FULL_ACCESS: true, SUPER_USERS: true},
  })),
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

describe('UseCurrentUser', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useCurrentUser', () => {
    it('returns user data and isSuperUser=true for superuser', async () => {
      vi.mocked(fetchUser).mockResolvedValueOnce({
        username: 'admin',
        super_user: true,
        global_readonly_super_user: false,
      } as any);
      const {result} = renderHook(() => useCurrentUser(), {wrapper});
      await waitFor(() => expect(result.current.user).toBeDefined());
      expect(result.current.user?.username).toBe('admin');
      expect(result.current.isSuperUser).toBe(true);
      expect(result.current.loading).toBe(false);
    });

    it('returns isSuperUser=false for regular user', async () => {
      vi.mocked(fetchUser).mockResolvedValueOnce({
        username: 'regularuser',
        super_user: false,
        global_readonly_super_user: false,
      } as any);
      const {result} = renderHook(() => useCurrentUser(), {wrapper});
      await waitFor(() => expect(result.current.user).toBeDefined());
      expect(result.current.isSuperUser).toBe(false);
    });
  });

  describe('useUpdateUser', () => {
    it('calls updateUser and fires onSuccess', async () => {
      const updatedUser = {username: 'admin', email: 'new@example.com'};
      vi.mocked(updateUser).mockResolvedValueOnce(updatedUser as any);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(() => useUpdateUser({onSuccess, onError}), {
        wrapper,
      });
      act(() => {
        result.current.updateUser({email: 'new@example.com'} as any);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(updatedUser));
    });

    it('fires onError on failure', async () => {
      const err = new Error('Update failed');
      vi.mocked(updateUser).mockRejectedValueOnce(err);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(() => useUpdateUser({onSuccess, onError}), {
        wrapper,
      });
      act(() => {
        result.current.updateUser({email: 'bad@example.com'} as any);
      });
      await waitFor(() => expect(onError).toHaveBeenCalledWith(err));
    });
  });

  describe('useChangeEmail', () => {
    it('calls updateUser with email and fires onSuccess', async () => {
      vi.mocked(updateUser).mockResolvedValueOnce({} as any);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(() => useChangeEmail({onSuccess, onError}), {
        wrapper,
      });
      act(() => {
        result.current.changeEmail('new@example.com');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(updateUser).toHaveBeenCalledWith({email: 'new@example.com'});
    });
  });
});
