import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useRepositoryState} from './UseRepositoryState';
import {setRepositoryState} from 'src/resources/RepositoryResource';

vi.mock('src/resources/RepositoryResource', () => ({
  setRepositoryState: vi.fn(),
  RepositoryState: {NORMAL: 'NORMAL', READONLY: 'READONLY', MIRROR: 'MIRROR'},
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

describe('useRepositoryState', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('calls setRepositoryState on mutation', async () => {
    vi.mocked(setRepositoryState).mockResolvedValueOnce(undefined);
    const {result} = renderHook(
      () => useRepositoryState('myorg', 'myrepo', 'NORMAL' as any),
      {wrapper},
    );
    act(() => {
      result.current.setState('READONLY' as any);
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(setRepositoryState).toHaveBeenCalledWith(
      'myorg',
      'myrepo',
      'READONLY',
    );
  });

  it('reports error on state change failure', async () => {
    vi.mocked(setRepositoryState).mockRejectedValueOnce(new Error('fail'));
    const {result} = renderHook(
      () => useRepositoryState('myorg', 'myrepo', 'NORMAL' as any),
      {wrapper},
    );
    act(() => {
      result.current.setState('READONLY' as any);
    });
    await waitFor(() => expect(result.current.error).toBe(true));
  });
});
