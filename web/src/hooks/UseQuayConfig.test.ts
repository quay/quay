import {renderHook, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useQuayConfig, useQuayConfigWithLoading} from './UseQuayConfig';
import {fetchQuayConfig} from 'src/resources/QuayConfig';

vi.mock('src/resources/QuayConfig', () => ({
  fetchQuayConfig: vi.fn(),
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

const mockConfig = {
  features: {BILLING: true, DIRECT_LOGIN: true},
  config: {REGISTRY_TITLE: 'Quay'},
  registry_state: 'normal',
};

describe('UseQuayConfig', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useQuayConfig', () => {
    it('returns config data on success', async () => {
      vi.mocked(fetchQuayConfig).mockResolvedValueOnce(mockConfig as any);
      const {result} = renderHook(() => useQuayConfig(), {wrapper});
      await waitFor(() => expect(result.current).toBeDefined());
      expect(result.current).toEqual(mockConfig);
    });

    it('returns undefined before data loads', () => {
      vi.mocked(fetchQuayConfig).mockImplementation(() => new Promise(vi.fn()));
      const {result} = renderHook(() => useQuayConfig(), {wrapper});
      expect(result.current).toBeUndefined();
    });
  });

  describe('useQuayConfigWithLoading', () => {
    it('returns config and loading state', async () => {
      vi.mocked(fetchQuayConfig).mockResolvedValueOnce(mockConfig as any);
      const {result} = renderHook(() => useQuayConfigWithLoading(), {wrapper});
      await waitFor(() => expect(result.current.config).toBeDefined());
      expect(result.current.config).toEqual(mockConfig);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });
});
