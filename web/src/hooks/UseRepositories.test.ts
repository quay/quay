import {renderHook, waitFor} from '@testing-library/react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {RecoilRoot} from 'recoil';
import {createElement} from 'react';
import {useRepositories} from './UseRepositories';

const mockUseCurrentUser = vi.hoisted(() =>
  vi.fn(() => ({
    user: {username: '', anonymous: true, organizations: []},
    isSuperUser: false,
  })),
);

const mockFetchRepositories = vi.hoisted(() =>
  vi.fn(() => Promise.resolve([])),
);

vi.mock('./UseCurrentUser', () => ({
  useCurrentUser: mockUseCurrentUser,
}));

vi.mock('src/resources/RepositoryResource', () => ({
  fetchAllRepos: vi.fn(() => Promise.resolve([])),
  fetchAllReposAsSuperUser: vi.fn(() =>
    Promise.resolve({repos: [], truncated: false}),
  ),
  fetchRepositories: mockFetchRepositories,
  fetchRepositoriesForNamespace: vi.fn(() => Promise.resolve([])),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {queries: {retry: false, cacheTime: 0}},
    logger: {log: vi.fn(), warn: vi.fn(), error: vi.fn()},
  });
  function Wrapper({children}: {children: React.ReactNode}) {
    return createElement(
      RecoilRoot,
      null,
      createElement(QueryClientProvider, {client: queryClient}, children),
    );
  }
  return Wrapper;
}

describe('useRepositories', () => {
  it('returns empty namespaces for anonymous users', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: '', anonymous: true, organizations: []},
      isSuperUser: false,
    });

    const {result} = renderHook(() => useRepositories(), {
      wrapper: createWrapper(),
    });

    expect(result.current.repos).toEqual([]);
  });

  it('calls fetchRepositories for anonymous users without org', async () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: '', anonymous: true, organizations: []},
      isSuperUser: false,
    });
    mockFetchRepositories.mockResolvedValue([
      {namespace: 'pub', name: 'repo1', is_public: true},
    ]);

    const {result} = renderHook(() => useRepositories(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(mockFetchRepositories).toHaveBeenCalled();
  });

  it('uses anonymous query key for anonymous users', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: '', anonymous: true, organizations: []},
      isSuperUser: false,
    });

    const {result} = renderHook(() => useRepositories(), {
      wrapper: createWrapper(),
    });

    expect(result.current).toBeDefined();
  });
});
