import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useTeamSync, useRemoveTeamSync} from './UseTeamSync';
import {
  enableTeamSyncForOrg,
  removeTeamSyncForOrg,
} from 'src/resources/TeamSyncResource';

vi.mock('src/resources/TeamSyncResource', () => ({
  enableTeamSyncForOrg: vi.fn(),
  removeTeamSyncForOrg: vi.fn(),
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

describe('UseTeamSync', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useTeamSync', () => {
    it('calls enableTeamSyncForOrg and fires onSuccess', async () => {
      vi.mocked(enableTeamSyncForOrg).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () =>
          useTeamSync({
            orgName: 'myorg',
            teamName: 'myteam',
            onSuccess,
            onError,
          }),
        {wrapper},
      );
      act(() => {
        result.current.enableTeamSync('mygroup', 'ldap');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(enableTeamSyncForOrg).toHaveBeenCalledWith(
        'myorg',
        'myteam',
        'mygroup',
        'ldap',
      );
    });

    it('calls onError with formatted message on failure', async () => {
      vi.mocked(enableTeamSyncForOrg).mockRejectedValueOnce(
        new Error('LDAP error'),
      );
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () =>
          useTeamSync({
            orgName: 'myorg',
            teamName: 'myteam',
            onSuccess,
            onError,
          }),
        {wrapper},
      );
      act(() => {
        result.current.enableTeamSync('badgroup', 'ldap');
      });
      await waitFor(() => expect(onError).toHaveBeenCalled());
      expect(onError).toHaveBeenCalledWith(
        expect.stringContaining('Error updating team sync config'),
      );
    });
  });

  describe('useRemoveTeamSync', () => {
    it('calls removeTeamSyncForOrg and fires onSuccess', async () => {
      vi.mocked(removeTeamSyncForOrg).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () =>
          useRemoveTeamSync({
            orgName: 'myorg',
            teamName: 'myteam',
            onSuccess,
            onError,
          }),
        {wrapper},
      );
      act(() => {
        result.current.removeTeamSync();
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(removeTeamSyncForOrg).toHaveBeenCalledWith('myorg', 'myteam');
    });
  });
});
