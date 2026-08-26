import {renderHook, act, screen, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useFetchOAuthApplications,
  useFetchOAuthApplicationTokens,
  useCreateOAuthApplicationToken,
  useAssignOAuthApplicationTokenToUser,
  useRevokeOAuthApplicationToken,
  useCreateOAuthApplication,
  useDeleteOAuthApplication,
  useUpdateOAuthApplication,
} from './UseOAuthApplications';
import ErrorBoundary from 'src/components/errors/ErrorBoundary';
import type {IOAuthApplicationToken} from 'src/resources/OAuthApplicationTypes';
import {
  fetchOAuthApplications,
  fetchOAuthApplicationTokens,
  createOAuthApplicationToken,
  assignOAuthApplicationTokenToUser,
  revokeOAuthApplicationToken,
  createOAuthApplication,
  deleteOAuthApplication,
  updateOAuthApplication,
} from 'src/resources/OAuthApplicationResource';

vi.mock('src/resources/OAuthApplicationResource', () => ({
  fetchOAuthApplications: vi.fn(),
  fetchOAuthApplicationTokens: vi.fn(),
  createOAuthApplicationToken: vi.fn(),
  assignOAuthApplicationTokenToUser: vi.fn(),
  revokeOAuthApplicationToken: vi.fn(),
  createOAuthApplication: vi.fn(),
  deleteOAuthApplication: vi.fn(),
  updateOAuthApplication: vi.fn(),
  bulkDeleteOAuthApplications: vi.fn(),
  resetOAuthApplicationClientSecret: vi.fn(),
}));

vi.mock(
  'src/routes/OrganizationsList/Organization/Tabs/OAuthApplications/OAuthApplicationsList',
  () => ({
    oauthApplicationColumnName: {
      name: 'name',
      application_uri: 'application_uri',
    },
  }),
);

function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    React.createElement(React.Suspense, {fallback: null}, children),
  );
}

describe('UseOAuthApplications', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useFetchOAuthApplications', () => {
    it('fetches oauth applications', async () => {
      const mockApps = [
        {
          name: 'App1',
          client_id: 'cid1',
          redirect_uri: 'https://example.com',
          application_uri: '',
          avatar_email: '',
          client_secret: '',
          description: '',
        },
      ];
      vi.mocked(fetchOAuthApplications).mockResolvedValueOnce(mockApps as any);
      const {result} = renderHook(() => useFetchOAuthApplications('myorg'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.loading).toBe(false));
      expect(result.current.oauthApplications).toEqual(mockApps);
      expect(result.current.filteredOAuthApplications).toHaveLength(1);
    });

    it('filters applications by search query', async () => {
      const mockApps = [
        {
          name: 'Alpha',
          client_id: 'cid1',
          redirect_uri: '',
          application_uri: '',
          avatar_email: '',
          client_secret: '',
          description: '',
        },
        {
          name: 'Beta',
          client_id: 'cid2',
          redirect_uri: '',
          application_uri: '',
          avatar_email: '',
          client_secret: '',
          description: '',
        },
      ];
      vi.mocked(fetchOAuthApplications).mockResolvedValueOnce(mockApps as any);
      const {result} = renderHook(() => useFetchOAuthApplications('myorg'), {
        wrapper,
      });
      await waitFor(() => expect(result.current.loading).toBe(false));
      act(() => {
        result.current.setSearch({query: 'Alpha', field: 'name'});
      });
      expect(result.current.filteredOAuthApplications).toHaveLength(1);
      expect(result.current.filteredOAuthApplications[0].name).toBe('Alpha');
    });
  });

  describe('useFetchOAuthApplicationTokens', () => {
    it('fetches OAuth application tokens', async () => {
      const mockTokens: IOAuthApplicationToken[] = [
        {
          uuid: 'token1',
          name: 'Inventory token',
          scope: 'repo:read user:read',
          expires_at: null,
          created: '2026-01-01T00:00:00Z',
          created_by: 'testuser',
          last_accessed: null,
        },
      ];
      vi.mocked(fetchOAuthApplicationTokens).mockResolvedValueOnce(mockTokens);

      const {result} = renderHook(
        () => useFetchOAuthApplicationTokens('myorg', 'client1'),
        {wrapper},
      );

      await waitFor(() => expect(result.current.tokens).toEqual(mockTokens));
      expect(fetchOAuthApplicationTokens).toHaveBeenCalledWith(
        'myorg',
        'client1',
      );
    });

    it('throws an initial token-list failure to the error boundary', async () => {
      vi.spyOn(console, 'error').mockImplementation(() => undefined);
      vi.mocked(fetchOAuthApplicationTokens).mockRejectedValueOnce(
        new Error('Initial load failed'),
      );
      const queryClient = createTestQueryClient();
      const queryWrapper = ({children}: {children: React.ReactNode}) =>
        React.createElement(
          QueryClientProvider,
          {client: queryClient},
          React.createElement(
            ErrorBoundary,
            {
              fallback: React.createElement(
                'span',
                {'data-testid': 'token-query-error'},
                'Unable to load API access tokens',
              ),
            },
            React.createElement(React.Suspense, {fallback: null}, children),
          ),
        );

      renderHook(() => useFetchOAuthApplicationTokens('myorg', 'client1'), {
        wrapper: queryWrapper,
      });

      expect(await screen.findByTestId('token-query-error')).toBeVisible();
    });

    it('preserves cached tokens and reports a background refresh failure separately', async () => {
      const mockTokens: IOAuthApplicationToken[] = [
        {
          uuid: 'token1',
          name: 'Inventory token',
          scope: 'repo:read',
          expires_at: null,
          created: '2026-01-01T00:00:00Z',
          created_by: 'testuser',
          last_accessed: null,
        },
      ];
      vi.mocked(fetchOAuthApplicationTokens)
        .mockResolvedValueOnce(mockTokens)
        .mockRejectedValueOnce(new Error('Refresh failed'));
      const queryClient = createTestQueryClient();
      const queryWrapper = ({children}: {children: React.ReactNode}) =>
        React.createElement(
          QueryClientProvider,
          {client: queryClient},
          React.createElement(React.Suspense, {fallback: null}, children),
        );

      const {result} = renderHook(
        () => useFetchOAuthApplicationTokens('myorg', 'client1'),
        {wrapper: queryWrapper},
      );
      await waitFor(() => expect(result.current.tokens).toEqual(mockTokens));

      await act(async () => {
        await queryClient.invalidateQueries([
          'oauthapplicationtokens',
          'myorg',
          'client1',
        ]);
      });

      await waitFor(() =>
        expect(result.current.errorRefreshingOAuthApplicationTokens).toBe(true),
      );
      expect(result.current.tokens).toEqual(mockTokens);
    });
  });

  describe('useCreateOAuthApplicationToken', () => {
    it('calls createOAuthApplicationToken and fires onSuccess', async () => {
      const createdToken: IOAuthApplicationToken = {
        uuid: 'token1',
        name: 'Generated token',
        scope: 'repo:read',
        expires_at: '2026-01-01T01:00:00Z',
        created: '2026-01-01T00:00:00Z',
        created_by: 'testuser',
        last_accessed: null,
        token: 'secret-token',
      };
      vi.mocked(createOAuthApplicationToken).mockResolvedValueOnce(
        createdToken,
      );
      const onSuccess = vi.fn();
      const {result} = renderHook(
        () => useCreateOAuthApplicationToken('myorg', 'client1', onSuccess),
        {wrapper},
      );
      const params = {
        name: 'Generated token',
        scope: 'repo:read',
        expiration: 3600,
      };

      await act(async () => {
        await result.current.createOAuthApplicationTokenMutationAsync(params);
      });

      await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(createdToken));
      expect(createOAuthApplicationToken).toHaveBeenCalledWith(
        'myorg',
        'client1',
        params,
      );
    });
  });

  describe('useAssignOAuthApplicationTokenToUser', () => {
    it('calls assignOAuthApplicationTokenToUser and fires onSuccess', async () => {
      const response = {message: 'Token assigned successfully'};
      vi.mocked(assignOAuthApplicationTokenToUser).mockResolvedValueOnce(
        response,
      );
      const onSuccess = vi.fn();
      const {result} = renderHook(
        () => useAssignOAuthApplicationTokenToUser('client1', onSuccess),
        {wrapper},
      );
      const params = {
        username: 'alice',
        scope: 'repo:read',
        redirect_uri: 'http://localhost/oauth/localapp',
      };

      await act(async () => {
        await result.current.assignOAuthApplicationTokenToUserMutationAsync(
          params,
        );
      });

      await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(response));
      expect(assignOAuthApplicationTokenToUser).toHaveBeenCalledWith(
        'client1',
        params,
      );
    });
  });

  describe('useRevokeOAuthApplicationToken', () => {
    it('calls revokeOAuthApplicationToken and fires onSuccess', async () => {
      vi.mocked(revokeOAuthApplicationToken).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const {result} = renderHook(
        () => useRevokeOAuthApplicationToken('myorg', 'client1', onSuccess),
        {wrapper},
      );

      await act(async () => {
        await result.current.revokeOAuthApplicationTokenMutationAsync('token1');
      });

      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(revokeOAuthApplicationToken).toHaveBeenCalledWith(
        'myorg',
        'client1',
        'token1',
      );
    });
  });

  describe('useCreateOAuthApplication', () => {
    it('calls createOAuthApplication and fires onSuccess', async () => {
      vi.mocked(createOAuthApplication).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useCreateOAuthApplication('myorg', {onSuccess, onError}),
        {wrapper},
      );
      const params = {
        name: 'NewApp',
        redirect_uri: 'https://example.com',
        application_uri: '',
        description: '',
        avatar_email: '',
      };
      act(() => {
        result.current.createOAuthApplication(params);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(createOAuthApplication).toHaveBeenCalledWith('myorg', params);
    });
  });

  describe('useDeleteOAuthApplication', () => {
    it('calls deleteOAuthApplication and sets successDeleteOAuthApplication', async () => {
      vi.mocked(deleteOAuthApplication).mockResolvedValueOnce(undefined);
      const {result} = renderHook(() => useDeleteOAuthApplication('myorg'), {
        wrapper,
      });
      const app = {name: 'App1', client_id: 'cid1'} as any;
      act(() => {
        result.current.removeOAuthApplication({oauthApp: app});
      });
      await waitFor(() =>
        expect(result.current.successDeleteOAuthApplication).toBe(true),
      );
      expect(deleteOAuthApplication).toHaveBeenCalledWith('myorg', app);
    });
  });

  describe('useUpdateOAuthApplication', () => {
    it('calls updateOAuthApplication and fires onSuccess', async () => {
      vi.mocked(updateOAuthApplication).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const {result} = renderHook(
        () => useUpdateOAuthApplication('myorg', onSuccess),
        {wrapper},
      );
      act(() => {
        result.current.updateOAuthApplicationMutation({
          clientId: 'cid1',
          applicationData: {name: 'Updated'},
        });
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(updateOAuthApplication).toHaveBeenCalledWith('myorg', 'cid1', {
        name: 'Updated',
      });
    });
  });
});
