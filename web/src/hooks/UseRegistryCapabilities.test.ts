import {renderHook, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useRegistryCapabilities,
  useMirrorArchitectures,
  useSparseManifestsSupported,
} from './UseRegistryCapabilities';
import {fetchRegistryCapabilities} from 'src/resources/CapabilitiesResource';

vi.mock('src/resources/CapabilitiesResource', () => ({
  fetchRegistryCapabilities: vi.fn(),
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

const mockCapabilities = {
  mirror_architectures: ['amd64', 'arm64'],
  sparse_manifests: {supported: true},
};

describe('UseRegistryCapabilities', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useRegistryCapabilities', () => {
    it('fetches and returns capabilities', async () => {
      vi.mocked(fetchRegistryCapabilities).mockResolvedValueOnce(
        mockCapabilities as any,
      );
      const {result} = renderHook(() => useRegistryCapabilities(), {wrapper});
      await waitFor(() => expect(result.current.capabilities).toBeDefined());
      expect(result.current.capabilities).toEqual(mockCapabilities);
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('useMirrorArchitectures', () => {
    it('returns mirror architectures list', async () => {
      vi.mocked(fetchRegistryCapabilities).mockResolvedValueOnce(
        mockCapabilities as any,
      );
      const {result} = renderHook(() => useMirrorArchitectures(), {wrapper});
      await waitFor(() => expect(result.current.architectures).toHaveLength(2));
      expect(result.current.architectures).toEqual(['amd64', 'arm64']);
    });

    it('returns empty array when capabilities unavailable', async () => {
      vi.mocked(fetchRegistryCapabilities).mockResolvedValueOnce({} as any);
      const {result} = renderHook(() => useMirrorArchitectures(), {wrapper});
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.architectures).toEqual([]);
    });
  });

  describe('useSparseManifestsSupported', () => {
    it('returns true when sparse manifests are supported', async () => {
      vi.mocked(fetchRegistryCapabilities).mockResolvedValueOnce(
        mockCapabilities as any,
      );
      const {result} = renderHook(() => useSparseManifestsSupported(), {
        wrapper,
      });
      await waitFor(() => expect(result.current).toBe(true));
    });

    it('returns false when sparse manifests are not supported', async () => {
      vi.mocked(fetchRegistryCapabilities).mockResolvedValueOnce({
        mirror_architectures: [],
        sparse_manifests: {supported: false},
      } as any);
      const {result} = renderHook(() => useSparseManifestsSupported(), {
        wrapper,
      });
      await waitFor(() => expect(result.current).toBe(false));
    });
  });
});
