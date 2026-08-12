import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useDeleteRepositories} from './UseDeleteRepositories';
import {bulkDeleteRepositories} from 'src/resources/RepositoryResource';

vi.mock('src/resources/RepositoryResource', () => ({
  bulkDeleteRepositories: vi.fn(),
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

describe('useDeleteRepositories', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('calls bulkDeleteRepositories and fires onSuccess', async () => {
    vi.mocked(bulkDeleteRepositories).mockResolvedValueOnce(undefined);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(
      () => useDeleteRepositories({onSuccess, onError}),
      {wrapper},
    );
    const repos = [{namespace: 'myorg', name: 'myrepo'}] as any;
    act(() => {
      result.current.deleteRepositories(repos);
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(bulkDeleteRepositories).toHaveBeenCalledWith(repos);
  });

  it('fires onError on failure', async () => {
    const err = new Error('Delete failed');
    vi.mocked(bulkDeleteRepositories).mockRejectedValueOnce(err);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(
      () => useDeleteRepositories({onSuccess, onError}),
      {wrapper},
    );
    act(() => {
      result.current.deleteRepositories([] as any);
    });
    await waitFor(() => expect(onError).toHaveBeenCalledWith(err));
  });
});
