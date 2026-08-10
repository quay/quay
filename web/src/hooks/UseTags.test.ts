import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useAllTags,
  useCreateTag,
  useSetExpiration,
  useSetTagImmutability,
  useDeleteTag,
  useRestoreTag,
  usePermanentlyDeleteTag,
  useTagPullStatistics,
} from './UseTags';
import {
  getTags,
  createTag,
  bulkSetExpiration,
  bulkSetTagImmutability,
  bulkDeleteTags,
  restoreTag,
  permanentlyDeleteTag,
  getTagPullStatistics,
} from 'src/resources/TagResource';
import {ResourceError} from 'src/resources/ErrorHandling';

vi.mock('src/resources/TagResource', () => ({
  getTags: vi.fn(),
  createTag: vi.fn(),
  bulkSetExpiration: vi.fn(),
  bulkSetTagImmutability: vi.fn(),
  bulkDeleteTags: vi.fn(),
  restoreTag: vi.fn(),
  permanentlyDeleteTag: vi.fn(),
  getTagPullStatistics: vi.fn(),
}));

vi.mock('src/resources/ErrorHandling', () => ({
  ResourceError: class ResourceError extends Error {
    status: number;
    error: unknown;
    constructor(message: string, status?: number, error?: unknown) {
      super(message);
      this.status = status;
      this.error = error;
    }
  },
  BulkOperationError: class BulkOperationError extends Error {},
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

describe('UseTags', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useAllTags', () => {
    it('returns tags from successful query', async () => {
      const mockTags = [{name: 'latest'}, {name: 'v1.0'}];
      vi.mocked(getTags).mockResolvedValueOnce({tags: mockTags} as any);
      const {result} = renderHook(() => useAllTags('myorg', 'myrepo'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.loadingTags).toBe(false));
      expect(result.current.tags).toEqual(mockTags);
      expect(result.current.errorLoadingTags).toBe(false);
    });

    it('returns empty array when response has no tags', async () => {
      vi.mocked(getTags).mockResolvedValueOnce({tags: null} as any);
      const {result} = renderHook(() => useAllTags('myorg', 'myrepo'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.loadingTags).toBe(false));
      expect(result.current.tags).toEqual([]);
    });

    it('reports error on query failure', async () => {
      vi.mocked(getTags).mockRejectedValueOnce(new Error('Network error'));
      const {result} = renderHook(() => useAllTags('myorg', 'myrepo'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.errorLoadingTags).toBe(true));
    });
  });

  describe('useCreateTag', () => {
    it('calls createTag resource function on mutate', async () => {
      vi.mocked(createTag).mockResolvedValueOnce(undefined);
      const {result} = renderHook(() => useCreateTag('myorg', 'myrepo'), {
        wrapper,
      });
      act(() => {
        result.current.createTag({tag: 'v2.0', manifest: 'sha256:abc'});
      });
      await waitFor(() => expect(result.current.successCreateTag).toBe(true));
      expect(createTag).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        'v2.0',
        'sha256:abc',
      );
    });

    it('reports error on createTag failure', async () => {
      vi.mocked(createTag).mockRejectedValueOnce(new Error('fail'));
      const {result} = renderHook(() => useCreateTag('myorg', 'myrepo'), {
        wrapper,
      });
      act(() => {
        result.current.createTag({tag: 'v2.0', manifest: 'sha256:abc'});
      });
      await waitFor(() => expect(result.current.errorCreateTag).toBe(true));
    });
  });

  describe('useSetExpiration', () => {
    it('calls bulkSetExpiration and reports success', async () => {
      vi.mocked(bulkSetExpiration).mockResolvedValueOnce(undefined);
      const {result} = renderHook(() => useSetExpiration('myorg', 'myrepo'), {
        wrapper,
      });
      act(() => {
        result.current.setExpiration({
          tags: ['latest', 'v1.0'],
          expiration: 1700000000,
        });
      });
      await waitFor(() =>
        expect(result.current.successSetExpiration).toBe(true),
      );
      expect(bulkSetExpiration).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        ['latest', 'v1.0'],
        1700000000,
      );
    });
  });

  describe('useSetTagImmutability', () => {
    it('calls bulkSetTagImmutability and reports success', async () => {
      vi.mocked(bulkSetTagImmutability).mockResolvedValueOnce(undefined);
      const {result} = renderHook(
        () => useSetTagImmutability('myorg', 'myrepo'),
        {wrapper},
      );
      act(() => {
        result.current.setImmutability({tags: ['latest'], immutable: true});
      });
      await waitFor(() =>
        expect(result.current.successSetImmutability).toBe(true),
      );
      expect(bulkSetTagImmutability).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        ['latest'],
        true,
      );
    });
  });

  describe('useDeleteTag', () => {
    it('calls bulkDeleteTags and reports success', async () => {
      vi.mocked(bulkDeleteTags).mockResolvedValueOnce(undefined);
      const {result} = renderHook(() => useDeleteTag('myorg', 'myrepo'), {
        wrapper,
      });
      act(() => {
        result.current.deleteTags({tags: ['old'], force: false});
      });
      await waitFor(() => expect(result.current.successDeleteTags).toBe(true));
      expect(bulkDeleteTags).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        ['old'],
        false,
      );
    });
  });

  describe('useRestoreTag', () => {
    it('calls restoreTag and invalidates query on success', async () => {
      vi.mocked(restoreTag).mockResolvedValueOnce(undefined);
      const {result} = renderHook(() => useRestoreTag('myorg', 'myrepo'), {
        wrapper,
      });
      act(() => {
        result.current.restoreTag({tag: 'old', digest: 'sha256:abc'});
      });
      await waitFor(() => expect(result.current.success).toBe(true));
      expect(restoreTag).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        'old',
        'sha256:abc',
      );
    });

    it('reports error on restoreTag failure', async () => {
      vi.mocked(restoreTag).mockRejectedValueOnce(new Error('fail'));
      const {result} = renderHook(() => useRestoreTag('myorg', 'myrepo'), {
        wrapper,
      });
      act(() => {
        result.current.restoreTag({tag: 'old', digest: 'sha256:abc'});
      });
      await waitFor(() => expect(result.current.error).toBe(true));
    });
  });

  describe('usePermanentlyDeleteTag', () => {
    it('calls permanentlyDeleteTag and reports success', async () => {
      vi.mocked(permanentlyDeleteTag).mockResolvedValueOnce(undefined);
      const {result} = renderHook(
        () => usePermanentlyDeleteTag('myorg', 'myrepo'),
        {wrapper},
      );
      act(() => {
        result.current.permanentlyDeleteTag({
          tag: 'old',
          digest: 'sha256:abc',
        });
      });
      await waitFor(() => expect(result.current.success).toBe(true));
      expect(permanentlyDeleteTag).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        'old',
        'sha256:abc',
      );
    });
  });

  describe('useTagPullStatistics', () => {
    it('returns pull statistics data on success', async () => {
      const mockData = {
        tag_name: 'latest',
        tag_pull_count: 42,
        last_tag_pull_date: '2024-01-01',
        current_manifest_digest: 'sha256:abc',
        last_manifest_pull_date: '2024-01-01',
      };
      vi.mocked(getTagPullStatistics).mockResolvedValueOnce(mockData as any);
      const {result} = renderHook(
        () => useTagPullStatistics('myorg', 'myrepo', 'latest'),
        {wrapper},
      );
      await waitFor(() =>
        expect(result.current.pullStatistics).toEqual(mockData),
      );
      expect(result.current.isError).toBe(false);
    });

    it('does not fetch when enabled=false', () => {
      renderHook(
        () => useTagPullStatistics('myorg', 'myrepo', 'latest', false),
        {wrapper},
      );
      expect(getTagPullStatistics).not.toHaveBeenCalled();
    });

    it('returns zero-pull defaults on 404 and does not report error', async () => {
      const notFoundError = new (vi.mocked(ResourceError) as any)(
        'Not found',
        404,
        {response: {status: 404}},
      );
      vi.mocked(getTagPullStatistics).mockRejectedValueOnce(notFoundError);
      const {result} = renderHook(
        () => useTagPullStatistics('myorg', 'myrepo', 'latest'),
        {wrapper},
      );
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      // 404 should not be reported as error
      expect(result.current.isError).toBe(false);
    });

    it('reports isError for non-404 errors', async () => {
      const serverError = new Error('Server error');
      vi.mocked(getTagPullStatistics).mockRejectedValueOnce(serverError);
      const {result} = renderHook(
        () => useTagPullStatistics('myorg', 'myrepo', 'latest'),
        {wrapper},
      );
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.isError).toBe(true);
    });
  });
});
