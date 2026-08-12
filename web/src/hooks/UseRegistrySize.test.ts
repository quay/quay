import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useRegistrySize,
  useQueueRegistrySizeCalculation,
} from './UseRegistrySize';
import {
  fetchRegistrySize,
  queueRegistrySizeCalculation,
} from 'src/resources/RegistrySizeResource';

vi.mock('src/resources/RegistrySizeResource', () => ({
  fetchRegistrySize: vi.fn(),
  queueRegistrySizeCalculation: vi.fn(),
}));

vi.mock('src/resources/ErrorHandling', () => ({
  addDisplayError: vi.fn((msg: string, err: Error) => `${msg}: ${err.message}`),
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

describe('UseRegistrySize', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useRegistrySize', () => {
    it('fetches registry size data', async () => {
      const mockSize = {size_bytes: 1073741824, running: false};
      vi.mocked(fetchRegistrySize).mockResolvedValueOnce(mockSize as any);
      const {result} = renderHook(() => useRegistrySize(), {wrapper});
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.registrySize).toEqual(mockSize);
    });

    it('does not fetch when enabled=false', () => {
      renderHook(() => useRegistrySize(false), {wrapper});
      expect(fetchRegistrySize).not.toHaveBeenCalled();
    });
  });

  describe('useQueueRegistrySizeCalculation', () => {
    it('calls queueRegistrySizeCalculation and fires onSuccess', async () => {
      vi.mocked(queueRegistrySizeCalculation).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useQueueRegistrySizeCalculation({onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.queueCalculation(undefined);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    });
  });
});
