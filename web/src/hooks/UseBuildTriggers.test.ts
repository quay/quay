import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useBuildTriggers,
  useFetchBuildTrigger,
  useToggleBuildTrigger,
  useDeleteBuildTrigger,
  useAnalyzeBuildTrigger,
} from './UseBuildTriggers';
import {
  fetchBuildTriggers,
  fetchBuildTrigger,
  toggleBuildTrigger,
  deleteBuildTrigger,
  analyzeBuildTrigger,
} from 'src/resources/BuildResource';

vi.mock('src/resources/BuildResource', () => ({
  fetchBuildTriggers: vi.fn(),
  fetchBuildTrigger: vi.fn(),
  toggleBuildTrigger: vi.fn(),
  deleteBuildTrigger: vi.fn(),
  analyzeBuildTrigger: vi.fn(),
  activateBuildTrigger: vi.fn(),
  fetchNamespaces: vi.fn(),
  fetchSources: vi.fn(),
  fetchRefs: vi.fn(),
  fetchSubDirs: vi.fn(),
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

describe('UseBuildTriggers', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useBuildTriggers', () => {
    it('fetches triggers and returns them', async () => {
      const mockTriggers = [{id: 't1', service: 'github'}];
      vi.mocked(fetchBuildTriggers).mockResolvedValueOnce(mockTriggers as any);
      const {result} = renderHook(() => useBuildTriggers('myorg', 'myrepo'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.triggers).toEqual(mockTriggers);
    });

    it('reports error on fetch failure', async () => {
      vi.mocked(fetchBuildTriggers).mockRejectedValueOnce(new Error('fail'));
      const {result} = renderHook(() => useBuildTriggers('myorg', 'myrepo'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe('useFetchBuildTrigger', () => {
    it('fetches a single trigger by uuid', async () => {
      const mockTrigger = {id: 't1', service: 'github'};
      vi.mocked(fetchBuildTrigger).mockResolvedValueOnce(mockTrigger as any);
      const {result} = renderHook(
        () => useFetchBuildTrigger('myorg', 'myrepo', 'trigger-uuid'),
        {wrapper},
      );
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.trigger).toEqual(mockTrigger);
    });

    it('does not fetch when triggerUuid is null', () => {
      renderHook(
        () =>
          useFetchBuildTrigger('myorg', 'myrepo', null as unknown as string),
        {wrapper},
      );
      expect(fetchBuildTrigger).not.toHaveBeenCalled();
    });
  });

  describe('useToggleBuildTrigger', () => {
    it('calls toggleBuildTrigger and fires onSuccess', async () => {
      vi.mocked(toggleBuildTrigger).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () =>
          useToggleBuildTrigger('myorg', 'myrepo', 'trigger-uuid', {
            onSuccess,
            onError,
          }),
        {wrapper},
      );
      act(() => {
        result.current.toggleTrigger(true);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(toggleBuildTrigger).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        'trigger-uuid',
        true,
      );
    });
  });

  describe('useDeleteBuildTrigger', () => {
    it('calls deleteBuildTrigger and fires onSuccess', async () => {
      vi.mocked(deleteBuildTrigger).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () =>
          useDeleteBuildTrigger('myorg', 'myrepo', 'trigger-uuid', {
            onSuccess,
            onError,
          }),
        {wrapper},
      );
      act(() => {
        result.current.deleteTrigger(undefined);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(deleteBuildTrigger).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        'trigger-uuid',
      );
    });
  });

  describe('useAnalyzeBuildTrigger', () => {
    it('fetches analysis when enabled', async () => {
      const mockAnalysis = {status: 'analyzed', config: {}};
      vi.mocked(analyzeBuildTrigger).mockResolvedValueOnce(mockAnalysis as any);
      const {result} = renderHook(
        () =>
          useAnalyzeBuildTrigger(
            'myorg',
            'myrepo',
            'trigger-uuid',
            'github.com/org/repo',
            '/context',
            '/Dockerfile',
            true,
          ),
        {wrapper},
      );
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.analysis).toEqual(mockAnalysis);
    });

    it('does not fetch when enabled=false', () => {
      renderHook(
        () =>
          useAnalyzeBuildTrigger(
            'myorg',
            'myrepo',
            'trigger-uuid',
            'source',
            '/ctx',
            '/Dockerfile',
            false,
          ),
        {wrapper},
      );
      expect(analyzeBuildTrigger).not.toHaveBeenCalled();
    });
  });
});
