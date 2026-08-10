import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useRepositoryVisibility} from './UseRepositoryVisibility';
import {setRepositoryVisibility} from 'src/resources/RepositoryResource';

vi.mock('src/resources/RepositoryResource', () => ({
  setRepositoryVisibility: vi.fn(),
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

describe('useRepositoryVisibility', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('calls setRepositoryVisibility on mutation', async () => {
    vi.mocked(setRepositoryVisibility).mockResolvedValueOnce(undefined);
    const {result} = renderHook(
      () => useRepositoryVisibility('myorg', 'myrepo'),
      {wrapper},
    );
    act(() => {
      result.current.setVisibility('public');
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(setRepositoryVisibility).toHaveBeenCalledWith(
      'myorg',
      'myrepo',
      'public',
    );
    expect(result.current.error).toBe(false);
  });

  it('reports error on visibility change failure', async () => {
    vi.mocked(setRepositoryVisibility).mockRejectedValueOnce(
      new Error('Unauthorized'),
    );
    const {result} = renderHook(
      () => useRepositoryVisibility('myorg', 'myrepo'),
      {wrapper},
    );
    act(() => {
      result.current.setVisibility('private');
    });
    await waitFor(() => expect(result.current.error).toBe(true));
  });
});
