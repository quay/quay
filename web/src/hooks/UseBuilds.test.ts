import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useBuilds,
  useRecentBuilds,
  useBuild,
  useStartBuild,
  useCancelBuild,
  useBuildLogs,
} from './UseBuilds';
import {
  fetchBuilds,
  fetchBuild,
  cancelBuild,
  startBuild,
  fetchBuildLogs,
} from 'src/resources/BuildResource';

vi.mock('src/resources/BuildResource', () => ({
  fetchBuilds: vi.fn(),
  fetchBuild: vi.fn(),
  cancelBuild: vi.fn(),
  startBuild: vi.fn(),
  fetchBuildLogs: vi.fn(),
  fileDrop: vi.fn(),
  uploadFile: vi.fn(),
  startDockerfileBuild: vi.fn(),
}));

vi.mock('src/libs/utils', () => ({
  isNullOrUndefined: (v: unknown) => v === null || v === undefined,
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

describe('UseBuilds', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useBuilds', () => {
    it('fetches builds without filter', async () => {
      const mockBuilds = [{id: 'b1', status: 'complete'}];
      vi.mocked(fetchBuilds).mockResolvedValueOnce(mockBuilds as any);
      const {result} = renderHook(() => useBuilds('myorg', 'myrepo'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.builds).toEqual(mockBuilds);
      expect(fetchBuilds).toHaveBeenCalledWith('myorg', 'myrepo', null);
    });

    it('fetches up to 100 builds when buildsSinceInSeconds is provided', async () => {
      vi.mocked(fetchBuilds).mockResolvedValueOnce([] as any);
      renderHook(() => useBuilds('myorg', 'myrepo', 3600), {wrapper});
      await waitFor(() => expect(fetchBuilds).toHaveBeenCalled());
      expect(fetchBuilds).toHaveBeenCalledWith('myorg', 'myrepo', 3600, 100);
    });

    it('reports error on fetch failure', async () => {
      vi.mocked(fetchBuilds).mockRejectedValueOnce(new Error('fail'));
      const {result} = renderHook(() => useBuilds('myorg', 'myrepo'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe('useRecentBuilds', () => {
    it('fetches builds with default limit of 3', async () => {
      vi.mocked(fetchBuilds).mockResolvedValueOnce([] as any);
      renderHook(() => useRecentBuilds('myorg', 'myrepo'), {wrapper});
      await waitFor(() => expect(fetchBuilds).toHaveBeenCalled());
      expect(fetchBuilds).toHaveBeenCalledWith('myorg', 'myrepo', null, 3);
    });
  });

  describe('useBuild', () => {
    it('fetches a single build by id', async () => {
      const mockBuild = {id: 'b1', status: 'running'};
      vi.mocked(fetchBuild).mockResolvedValueOnce(mockBuild as any);
      const {result} = renderHook(() => useBuild('myorg', 'myrepo', 'b1'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.build).toEqual(mockBuild);
    });
  });

  describe('useStartBuild', () => {
    it('calls startBuild and fires onSuccess', async () => {
      const mockData = {id: 'new-build'};
      vi.mocked(startBuild).mockResolvedValueOnce(mockData as any);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () =>
          useStartBuild('myorg', 'myrepo', 'trigger-uuid', {
            onSuccess,
            onError,
          }),
        {wrapper},
      );
      act(() => {
        result.current.startBuild('main');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(mockData));
      expect(startBuild).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        'trigger-uuid',
        'main',
      );
    });
  });

  describe('useCancelBuild', () => {
    it('calls cancelBuild and fires onSuccess', async () => {
      vi.mocked(cancelBuild).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useCancelBuild('myorg', 'myrepo', 'b1', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.cancelBuild(undefined);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    });
  });

  describe('useBuildLogs', () => {
    it('initializes with empty log entries', async () => {
      vi.mocked(fetchBuildLogs).mockResolvedValueOnce({
        start: 0,
        total: 0,
        logs: [],
      } as any);
      const {result} = renderHook(() => useBuildLogs('myorg', 'myrepo', 'b1'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.logs).toEqual([]);
    });

    it('parses command/phase/error type log entries as top-level entries', async () => {
      vi.mocked(fetchBuildLogs).mockResolvedValueOnce({
        start: 0,
        total: 3,
        logs: [
          {type: 'phase', message: 'Building'},
          {type: 'entry', message: 'sub log'},
          {type: 'command', message: 'RUN npm install'},
        ],
      } as any);
      const {result} = renderHook(() => useBuildLogs('myorg', 'myrepo', 'b1'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.logs).toHaveLength(2));
      expect(result.current.logs[0].type).toBe('phase');
      expect(result.current.logs[1].type).toBe('command');
      // sub log goes into parent's logs array
      expect(result.current.logs[0].logs).toHaveLength(1);
    });
  });
});
