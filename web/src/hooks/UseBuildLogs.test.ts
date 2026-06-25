import {renderHook, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useFetchBuildLogsSuperuser} from './UseBuildLogs';
import {fetchBuildLogsSuperuser} from 'src/resources/BuildResource';

vi.mock('src/resources/BuildResource', () => ({
  fetchBuildLogsSuperuser: vi.fn(),
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

describe('useFetchBuildLogsSuperuser', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('fetches build logs when buildUuid is provided', async () => {
    const mockBuild = {id: 'build-uuid-123', status: 'complete'};
    vi.mocked(fetchBuildLogsSuperuser).mockResolvedValueOnce(mockBuild as any);

    const {result} = renderHook(
      () => useFetchBuildLogsSuperuser('build-uuid-123'),
      {wrapper},
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockBuild);
    expect(fetchBuildLogsSuperuser).toHaveBeenCalledWith(
      'build-uuid-123',
      expect.any(Object),
    );
  });

  it('does not fetch when buildUuid is null', () => {
    renderHook(() => useFetchBuildLogsSuperuser(null), {wrapper});
    expect(fetchBuildLogsSuperuser).not.toHaveBeenCalled();
  });

  it('does not fetch when buildUuid is empty string', () => {
    renderHook(() => useFetchBuildLogsSuperuser(''), {wrapper});
    expect(fetchBuildLogsSuperuser).not.toHaveBeenCalled();
  });

  it('reports error on fetch failure', async () => {
    vi.mocked(fetchBuildLogsSuperuser).mockRejectedValueOnce(
      new Error('Not found'),
    );
    const {result} = renderHook(() => useFetchBuildLogsSuperuser('bad-uuid'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
