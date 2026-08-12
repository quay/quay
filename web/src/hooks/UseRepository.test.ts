import {renderHook, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useRepository, useTransitivePermissions} from './UseRepository';
import {
  fetchRepositoryDetails,
  fetchEntityTransitivePermission,
} from 'src/resources/RepositoryResource';

vi.mock('src/resources/RepositoryResource', () => ({
  fetchRepositoryDetails: vi.fn(),
  fetchEntityTransitivePermission: vi.fn(),
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

describe('UseRepository', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useRepository', () => {
    it('fetches repository details when repo is provided', async () => {
      const mockRepo = {name: 'myrepo', namespace: 'myorg', is_public: true};
      vi.mocked(fetchRepositoryDetails).mockResolvedValueOnce(mockRepo as any);
      const {result} = renderHook(() => useRepository('myorg', 'myrepo'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.repoDetails).toEqual(mockRepo);
    });

    it('does not fetch when repo is undefined', () => {
      renderHook(() => useRepository('myorg', undefined), {wrapper});
      expect(fetchRepositoryDetails).not.toHaveBeenCalled();
    });
  });

  describe('useTransitivePermissions', () => {
    it('fetches transitive permissions when entity is provided', async () => {
      const mockPerms = {role: 'read'};
      vi.mocked(fetchEntityTransitivePermission).mockResolvedValueOnce(
        mockPerms as any,
      );
      const {result} = renderHook(
        () => useTransitivePermissions('myorg', 'myrepo', 'alice'),
        {wrapper},
      );
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.permissions).toEqual(mockPerms);
    });

    it('does not fetch when entity is undefined', () => {
      renderHook(() => useTransitivePermissions('myorg', 'myrepo', undefined), {
        wrapper,
      });
      expect(fetchEntityTransitivePermission).not.toHaveBeenCalled();
    });
  });
});
