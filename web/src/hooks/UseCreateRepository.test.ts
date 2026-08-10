import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useCreateRepository} from './UseCreateRepository';
import {createNewRepository} from 'src/resources/RepositoryResource';

vi.mock('src/resources/RepositoryResource', () => ({
  createNewRepository: vi.fn(),
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

describe('useCreateRepository', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('calls createNewRepository and fires onSuccess', async () => {
    vi.mocked(createNewRepository).mockResolvedValueOnce({} as any);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(
      () => useCreateRepository({onSuccess, onError}),
      {wrapper},
    );
    act(() => {
      result.current.createRepository({
        namespace: 'myorg',
        repository: 'newrepo',
        visibility: 'private',
        description: 'A test repo',
        repo_kind: 'image',
      });
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(createNewRepository).toHaveBeenCalledWith(
      'myorg',
      'newrepo',
      'private',
      'A test repo',
      'image',
    );
  });

  it('fires onError on failure', async () => {
    const err = new Error('Already exists');
    vi.mocked(createNewRepository).mockRejectedValueOnce(err);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(
      () => useCreateRepository({onSuccess, onError}),
      {wrapper},
    );
    act(() => {
      result.current.createRepository({
        namespace: 'myorg',
        repository: 'existing',
        visibility: 'public',
        description: '',
        repo_kind: 'image',
      });
    });
    await waitFor(() => expect(onError).toHaveBeenCalledWith(err));
  });
});
