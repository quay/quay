import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useFetchProxyCacheConfig,
  useCreateProxyCacheConfig,
  useDeleteProxyCacheConfig,
} from './UseProxyCache';
import {
  fetchProxyCacheConfig,
  createProxyCacheConfig,
  deleteProxyCacheConfig,
} from 'src/resources/ProxyCacheResource';

vi.mock('src/resources/ProxyCacheResource', () => ({
  fetchProxyCacheConfig: vi.fn(),
  validateProxyCacheConfig: vi.fn(),
  createProxyCacheConfig: vi.fn(),
  deleteProxyCacheConfig: vi.fn(),
}));

vi.mock('src/resources/ErrorHandling', () => ({
  addDisplayError: vi.fn((msg: string, err: Error) => `${msg}: ${err.message}`),
}));

vi.mock('axios', () => ({
  isAxiosError: (err: unknown) => (err as any)?._isAxiosError === true,
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

describe('UseProxyCache', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useFetchProxyCacheConfig', () => {
    it('fetches proxy cache config', async () => {
      const mockConfig = {
        upstream_registry: 'registry.example.com',
        expiration_s: 86400,
      };
      vi.mocked(fetchProxyCacheConfig).mockResolvedValueOnce(mockConfig as any);
      const {result} = renderHook(() => useFetchProxyCacheConfig('myorg'), {
        wrapper,
      });
      await waitFor(() =>
        expect(result.current.isSuccessLoadingProxyCacheConfig).toBe(true),
      );
      expect(result.current.fetchedProxyCacheConfig).toEqual(mockConfig);
      expect(result.current.isProxyCacheConfigured).toBe(true);
    });

    it('does not fetch when enabled=false', () => {
      renderHook(() => useFetchProxyCacheConfig('myorg', false), {wrapper});
      expect(fetchProxyCacheConfig).not.toHaveBeenCalled();
    });
  });

  describe('useCreateProxyCacheConfig', () => {
    it('calls createProxyCacheConfig and fires onSuccess', async () => {
      vi.mocked(createProxyCacheConfig).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useCreateProxyCacheConfig({onSuccess, onError}),
        {wrapper},
      );
      const config = {
        upstream_registry: 'registry.example.com',
        expiration_s: 86400,
      };
      act(() => {
        result.current.createProxyCacheConfigMutation(config as any);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    });
  });

  describe('useDeleteProxyCacheConfig', () => {
    it('calls deleteProxyCacheConfig and fires onSuccess', async () => {
      vi.mocked(deleteProxyCacheConfig).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useDeleteProxyCacheConfig('myorg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.deleteProxyCacheConfigMutation(undefined);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(deleteProxyCacheConfig).toHaveBeenCalledWith('myorg');
    });
  });
});
