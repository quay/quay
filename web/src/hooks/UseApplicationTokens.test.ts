import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useApplicationTokens,
  useFetchApplicationTokens,
  useCreateApplicationToken,
  useApplicationToken,
  useRevokeApplicationToken,
} from './UseApplicationTokens';
import {
  fetchApplicationTokens,
  fetchApplicationToken,
  createApplicationToken,
  revokeApplicationToken,
  ApplicationTokenError,
} from 'src/resources/UserResource';

vi.mock('src/resources/UserResource', () => ({
  fetchApplicationTokens: vi.fn(),
  fetchApplicationToken: vi.fn(),
  createApplicationToken: vi.fn(),
  revokeApplicationToken: vi.fn(),
  ApplicationTokenError: class ApplicationTokenError extends Error {
    constructor(message: string, code: string, cause?: unknown) {
      super(message);
    }
  },
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

const mockTokens = {
  tokens: [
    {uuid: 't1', title: 'CI Token', expiration: null},
    {uuid: 't2', title: 'Deploy Token', expiration: null},
  ],
};

describe('UseApplicationTokens', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useApplicationTokens', () => {
    it('fetches application tokens', async () => {
      vi.mocked(fetchApplicationTokens).mockResolvedValueOnce(
        mockTokens as any,
      );
      const {result} = renderHook(() => useApplicationTokens(), {wrapper});
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(mockTokens);
    });
  });

  describe('useFetchApplicationTokens', () => {
    it('returns paginated and filtered tokens', async () => {
      vi.mocked(fetchApplicationTokens).mockResolvedValueOnce(
        mockTokens as any,
      );
      const {result} = renderHook(() => useFetchApplicationTokens(), {wrapper});
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.tokens).toHaveLength(2);
      expect(result.current.filteredTokens).toHaveLength(2);
    });

    it('filters tokens by search query', async () => {
      vi.mocked(fetchApplicationTokens).mockResolvedValueOnce(
        mockTokens as any,
      );
      const {result} = renderHook(() => useFetchApplicationTokens(), {wrapper});
      await waitFor(() => expect(result.current.isLoading).toBe(false));
      act(() => {
        result.current.setSearch({query: 'CI', field: 'title'});
      });
      expect(result.current.filteredTokens).toHaveLength(1);
      expect(result.current.filteredTokens[0].title).toBe('CI Token');
    });
  });

  describe('useCreateApplicationToken', () => {
    it('calls createApplicationToken and fires onSuccess', async () => {
      const newToken = {uuid: 'new', title: 'New Token', token: 'secret'};
      vi.mocked(createApplicationToken).mockResolvedValueOnce(newToken as any);
      const onSuccess = vi.fn();
      const {result} = renderHook(
        () => useCreateApplicationToken({onSuccess}),
        {wrapper},
      );
      act(() => {
        result.current.mutate('New Token');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(newToken));
    });
  });

  describe('useApplicationToken', () => {
    it('fetches a single token when uuid is provided', async () => {
      const token = {uuid: 't1', title: 'CI Token'};
      vi.mocked(fetchApplicationToken).mockResolvedValueOnce(token as any);
      const {result} = renderHook(() => useApplicationToken('t1'), {wrapper});
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(token);
    });

    it('does not fetch when uuid is null', () => {
      renderHook(() => useApplicationToken(null), {wrapper});
      expect(fetchApplicationToken).not.toHaveBeenCalled();
    });
  });

  describe('useRevokeApplicationToken', () => {
    it('calls revokeApplicationToken and fires onSuccess', async () => {
      vi.mocked(revokeApplicationToken).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const {result} = renderHook(
        () => useRevokeApplicationToken({onSuccess}),
        {wrapper},
      );
      act(() => {
        result.current.mutate('t1');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(revokeApplicationToken).toHaveBeenCalledWith('t1');
    });
  });
});
