import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useChangeUserEmail,
  useChangeUserPassword,
  useToggleUserStatus,
  useDeleteUser,
  useSendRecoveryEmail,
} from './UseUserActions';
import {
  updateSuperuserUser,
  deleteSuperuserUser,
  sendRecoveryEmail,
} from 'src/resources/UserResource';

vi.mock('src/resources/UserResource', () => ({
  updateSuperuserUser: vi.fn(),
  deleteSuperuserUser: vi.fn(),
  sendRecoveryEmail: vi.fn(),
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

describe('UseUserActions', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useChangeUserEmail', () => {
    it('calls updateSuperuserUser with email and fires onSuccess', async () => {
      vi.mocked(updateSuperuserUser).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useChangeUserEmail({onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.changeEmail('alice', 'alice@new.com');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(updateSuperuserUser).toHaveBeenCalledWith('alice', {
        email: 'alice@new.com',
      });
    });
  });

  describe('useChangeUserPassword', () => {
    it('calls updateSuperuserUser with password', async () => {
      vi.mocked(updateSuperuserUser).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useChangeUserPassword({onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.changePassword('alice', 'newpass');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(updateSuperuserUser).toHaveBeenCalledWith('alice', {
        password: 'newpass',
      });
    });
  });

  describe('useToggleUserStatus', () => {
    it('calls updateSuperuserUser with enabled flag', async () => {
      vi.mocked(updateSuperuserUser).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useToggleUserStatus({onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.toggleStatus('alice', false);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(updateSuperuserUser).toHaveBeenCalledWith('alice', {
        enabled: false,
      });
    });
  });

  describe('useDeleteUser', () => {
    it('calls deleteSuperuserUser and fires onSuccess', async () => {
      vi.mocked(deleteSuperuserUser).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(() => useDeleteUser({onSuccess, onError}), {
        wrapper,
      });
      act(() => {
        result.current.deleteUser('alice');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(deleteSuperuserUser).toHaveBeenCalledWith('alice');
    });
  });

  describe('useSendRecoveryEmail', () => {
    it('calls sendRecoveryEmail and fires onSuccess with data', async () => {
      const mockData = {status: 'sent'};
      vi.mocked(sendRecoveryEmail).mockResolvedValueOnce(mockData as any);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useSendRecoveryEmail({onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.sendRecovery('alice');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(mockData));
      expect(sendRecoveryEmail).toHaveBeenCalledWith('alice');
    });
  });
});
