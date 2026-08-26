import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useRenameOrganization,
  useDeleteSingleOrganization,
  useTakeOwnership,
} from './UseOrganizationActions';
import {
  deleteOrg,
  renameOrganization,
  takeOwnership,
} from 'src/resources/OrganizationResource';

vi.mock('src/resources/OrganizationResource', () => ({
  deleteOrg: vi.fn(),
  renameOrganization: vi.fn(),
  takeOwnership: vi.fn(),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
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

describe('UseOrganizationActions', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useRenameOrganization', () => {
    it('calls renameOrganization and fires onSuccess with names', async () => {
      vi.mocked(renameOrganization).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useRenameOrganization({onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.renameOrganization('oldname', 'newname');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(onSuccess).toHaveBeenCalledWith('oldname', 'newname');
      expect(renameOrganization).toHaveBeenCalledWith('oldname', 'newname');
    });

    it('fires onError on failure', async () => {
      const err = new Error('Rename failed');
      vi.mocked(renameOrganization).mockRejectedValueOnce(err);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useRenameOrganization({onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.renameOrganization('oldname', 'newname');
      });
      await waitFor(() => expect(onError).toHaveBeenCalledWith(err));
      expect(onSuccess).not.toHaveBeenCalled();
    });
  });

  describe('useDeleteSingleOrganization', () => {
    it('calls deleteOrg with superuser=true and fires onSuccess', async () => {
      vi.mocked(deleteOrg).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useDeleteSingleOrganization({onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.deleteOrganization('myorg');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(deleteOrg).toHaveBeenCalledWith('myorg', true);
    });

    it('fires onError on failure', async () => {
      const err = new Error('Delete failed');
      vi.mocked(deleteOrg).mockRejectedValueOnce(err);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useDeleteSingleOrganization({onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.deleteOrganization('myorg');
      });
      await waitFor(() => expect(onError).toHaveBeenCalledWith(err));
    });
  });

  describe('useTakeOwnership', () => {
    it('calls takeOwnership and navigates to org page on success', async () => {
      vi.mocked(takeOwnership).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useTakeOwnership({onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.takeOwnership('myorg');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(takeOwnership).toHaveBeenCalledWith('myorg');
      expect(mockNavigate).toHaveBeenCalledWith('/organization/myorg');
    });

    it('fires onError on failure', async () => {
      const err = new Error('Take ownership failed');
      vi.mocked(takeOwnership).mockRejectedValueOnce(err);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useTakeOwnership({onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.takeOwnership('myorg');
      });
      await waitFor(() => expect(onError).toHaveBeenCalledWith(err));
    });
  });
});
