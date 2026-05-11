import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useAuthorizedApplications} from './UseAuthorizedApplications';
import axios from 'src/libs/axios';

vi.mock('src/libs/axios', () => ({
  default: {
    get: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('src/resources/ErrorHandling', () => ({
  assertHttpCode: vi.fn(),
}));

vi.mock('./UseCurrentUser', () => ({
  useCurrentUser: vi.fn(() => ({user: {username: 'testuser'}})),
}));

vi.mock('./UseQuayConfig', () => ({
  useQuayConfig: vi.fn(() => ({
    features: {ASSIGN_OAUTH_TOKEN: true},
  })),
}));

function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

const mockApp = {
  uuid: 'app-uuid-1',
  application: {
    name: 'TestApp',
    description: 'A test app',
    url: 'https://app.example.com',
    avatar: {name: 'test', hash: 'abc', command: [], kind: 'user'},
    organization: {name: 'myorg'},
    clientId: 'client-id-123',
  },
  scopes: [
    {scope: 'repo:read', description: 'Read repos'},
    {scope: 'repo:write', description: 'Write repos'},
  ],
};

describe('UseAuthorizedApplications', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches authorized and assigned apps', async () => {
    vi.mocked(axios.get).mockImplementation((url: string) => {
      if (url === '/api/v1/user/authorizations') {
        return Promise.resolve({
          status: 200,
          data: {authorizations: [mockApp]},
        });
      }
      if (url === '/api/v1/user/assignedauthorization') {
        return Promise.resolve({
          status: 200,
          data: {authorizations: []},
        });
      }
      return Promise.resolve({status: 200, data: {}});
    });

    const {result} = renderHook(() => useAuthorizedApplications(), {wrapper});
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.authorizedApps).toHaveLength(1);
    expect(result.current.authorizedApps[0].uuid).toBe('app-uuid-1');
    expect(result.current.assignedApps).toHaveLength(0);
  });

  it('revokes authorization', async () => {
    vi.mocked(axios.get).mockImplementation((url: string) => {
      if (url.includes('authorizations')) {
        return Promise.resolve({
          status: 200,
          data: {authorizations: [mockApp]},
        });
      }
      return Promise.resolve({status: 200, data: {authorizations: []}});
    });
    vi.mocked(axios.delete).mockResolvedValue({status: 204});

    const {result} = renderHook(() => useAuthorizedApplications(), {wrapper});
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.revokeAuthorization('app-uuid-1');
    });

    await waitFor(() =>
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/user/authorizations/app-uuid-1',
      ),
    );
  });

  it('generates correct authorization URL', async () => {
    vi.mocked(axios.get).mockResolvedValue({
      status: 200,
      data: {authorizations: [mockApp]},
    });

    const {result} = renderHook(() => useAuthorizedApplications(), {wrapper});
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    const url = result.current.getAuthorizationUrl(mockApp as any);
    expect(url).toContain('/oauth/authorize?');
    expect(url).toContain('client_id=client-id-123');
    expect(url).toContain('scope=repo%3Aread+repo%3Awrite');
    expect(url).toContain('assignment_uuid=app-uuid-1');
  });

  it('returns error when fetching fails', async () => {
    vi.mocked(axios.get).mockRejectedValue(new Error('Network error'));

    const {result} = renderHook(() => useAuthorizedApplications(), {wrapper});
    await waitFor(() => expect(result.current.error).toBeTruthy());
  });
});
