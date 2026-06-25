import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useDeleteAccount} from './UseDeleteAccount';
import {deleteUser} from 'src/resources/UserResource';
import {deleteOrg} from 'src/resources/OrganizationResource';

vi.mock('src/resources/UserResource', () => ({
  deleteUser: vi.fn(),
}));

vi.mock('src/resources/OrganizationResource', () => ({
  deleteOrg: vi.fn(),
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

describe('useDeleteAccount', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('calls deleteUser and fires onSuccess', async () => {
    vi.mocked(deleteUser).mockResolvedValueOnce(undefined);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(() => useDeleteAccount({onSuccess, onError}), {
      wrapper,
    });
    act(() => {
      result.current.deleteUser();
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });

  it('calls deleteOrg and fires onSuccess', async () => {
    vi.mocked(deleteOrg).mockResolvedValueOnce(undefined);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(() => useDeleteAccount({onSuccess, onError}), {
      wrapper,
    });
    act(() => {
      result.current.deleteOrg('myorg');
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(deleteOrg).toHaveBeenCalledWith('myorg');
  });

  it('fires onError when deleteUser fails', async () => {
    const err = new Error('Delete failed');
    vi.mocked(deleteUser).mockRejectedValueOnce(err);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(() => useDeleteAccount({onSuccess, onError}), {
      wrapper,
    });
    act(() => {
      result.current.deleteUser().catch(vi.fn());
    });
    await waitFor(() => expect(onError).toHaveBeenCalledWith(err));
  });
});
