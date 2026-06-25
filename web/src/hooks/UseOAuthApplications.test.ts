import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useFetchOAuthApplications,
  useCreateOAuthApplication,
  useDeleteOAuthApplication,
  useUpdateOAuthApplication,
} from './UseOAuthApplications';
import {
  fetchOAuthApplications,
  createOAuthApplication,
  deleteOAuthApplication,
  updateOAuthApplication,
} from 'src/resources/OAuthApplicationResource';

vi.mock('src/resources/OAuthApplicationResource', () => ({
  fetchOAuthApplications: vi.fn(),
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
    children,
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
