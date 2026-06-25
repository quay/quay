import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useLabels} from './UseTagLabels';
import {
  getLabels,
  bulkCreateLabels,
  bulkDeleteLabels,
} from 'src/resources/TagResource';

vi.mock('src/resources/TagResource', () => ({
  getLabels: vi.fn(),
  bulkCreateLabels: vi.fn(),
  bulkDeleteLabels: vi.fn(),
}));

vi.mock('src/resources/ErrorHandling', () => ({
  ResourceError: class ResourceError extends Error {},
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

describe('useLabels', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('fetches labels for a digest', async () => {
    const mockLabels = [
      {key: 'version', value: '1.0', mediatype: 'text/plain'},
    ];
    vi.mocked(getLabels).mockResolvedValueOnce(mockLabels as any);
    const {result} = renderHook(
      () => useLabels('myorg', 'myrepo', 'sha256:abc'),
      {wrapper},
    );
    await waitFor(() => expect(result.current.labels).toEqual(mockLabels));
  });

  it('calls bulkCreateLabels on createLabels mutate', async () => {
    vi.mocked(getLabels).mockResolvedValueOnce([]);
    vi.mocked(bulkCreateLabels).mockResolvedValueOnce(undefined);
    const {result} = renderHook(
      () => useLabels('myorg', 'myrepo', 'sha256:abc'),
      {wrapper},
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    const newLabel = {key: 'env', value: 'prod', mediatype: 'text/plain'};
    act(() => {
      result.current.createLabels([newLabel] as any);
    });
    await waitFor(() =>
      expect(result.current.successCreatingLabels).toBe(true),
    );
    expect(bulkCreateLabels).toHaveBeenCalledWith(
      'myorg',
      'myrepo',
      'sha256:abc',
      [newLabel],
    );
  });

  it('calls bulkDeleteLabels on deleteLabels mutate', async () => {
    vi.mocked(getLabels).mockResolvedValueOnce([]);
    vi.mocked(bulkDeleteLabels).mockResolvedValueOnce(undefined);
    const {result} = renderHook(
      () => useLabels('myorg', 'myrepo', 'sha256:abc'),
      {wrapper},
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.deleteLabels([{key: 'env', value: 'prod'}] as any);
    });
    await waitFor(() =>
      expect(result.current.successDeletingLabels).toBe(true),
    );
  });
});
