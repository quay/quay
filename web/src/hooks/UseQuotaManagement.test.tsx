import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useFetchOrganizationQuota,
  useCreateOrganizationQuota,
  useUpdateOrganizationQuota,
  useDeleteOrganizationQuota,
  useCreateQuotaLimit,
  useUpdateQuotaLimit,
  useDeleteQuotaLimit,
} from './UseQuotaManagement';
import {
  fetchOrganizationQuota,
  createOrganizationQuota,
  updateOrganizationQuota,
  deleteOrganizationQuota,
  createQuotaLimit,
  updateQuotaLimit,
  deleteQuotaLimit,
} from 'src/resources/QuotaResource';
import {addDisplayError} from 'src/resources/ErrorHandling';

vi.mock('src/resources/QuotaResource', () => ({
  fetchOrganizationQuota: vi.fn(),
  createOrganizationQuota: vi.fn(),
  updateOrganizationQuota: vi.fn(),
  deleteOrganizationQuota: vi.fn(),
  createQuotaLimit: vi.fn(),
  updateQuotaLimit: vi.fn(),
  deleteQuotaLimit: vi.fn(),
}));

vi.mock('src/resources/ErrorHandling', () => ({
  addDisplayError: vi.fn((msg: string, err: Error) => `${msg}: ${err.message}`),
}));

const mockQuota = {
  id: 'quota-1',
  limit_bytes: 1073741824,
  limits: [{id: 'limit-1', type: 'Warning' as const, limit_percent: 80}],
};

/** QueryClientProvider wrapper for hooks that use React Query. */
function wrapper({children}: {children: React.ReactNode}) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('UseQuotaManagement', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('useFetchOrganizationQuota', () => {
    it('returns null when no quota data exists', async () => {
      vi.mocked(fetchOrganizationQuota).mockResolvedValueOnce([]);
      const {result} = renderHook(() => useFetchOrganizationQuota('testOrg'), {
        wrapper,
      });
      await waitFor(() => {
        expect(result.current.isSuccessLoadingQuotas).toBe(true);
      });
      expect(result.current.organizationQuota).toBeNull();
    });

    it('returns first quota from array', async () => {
      vi.mocked(fetchOrganizationQuota).mockResolvedValueOnce([mockQuota]);
      const {result} = renderHook(() => useFetchOrganizationQuota('testOrg'), {
        wrapper,
      });
      await waitFor(() => {
        expect(result.current.organizationQuota).toEqual(mockQuota);
      });
    });

    it('does not fetch when orgName is empty and no viewMode', () => {
      renderHook(() => useFetchOrganizationQuota(''), {wrapper});
      expect(fetchOrganizationQuota).not.toHaveBeenCalled();
    });

    it('is enabled when viewMode is "self" even with empty orgName', async () => {
      vi.mocked(fetchOrganizationQuota).mockResolvedValueOnce([mockQuota]);
      const {result} = renderHook(() => useFetchOrganizationQuota('', 'self'), {
        wrapper,
      });
      await waitFor(() => {
        expect(fetchOrganizationQuota).toHaveBeenCalled();
      });
      await waitFor(() => {
        expect(result.current.organizationQuota).toEqual(mockQuota);
      });
    });
  });

  describe('useCreateOrganizationQuota', () => {
    it('calls resource function and fires onSuccess', async () => {
      vi.mocked(createOrganizationQuota).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useCreateOrganizationQuota('testOrg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.createQuotaMutation({limit_bytes: 1024});
      });
      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });
      expect(createOrganizationQuota).toHaveBeenCalledWith(
        'testOrg',
        {limit_bytes: 1024},
        undefined,
      );
    });

    it('fires onError with addDisplayError on failure', async () => {
      const error = new Error('Network error');
      vi.mocked(createOrganizationQuota).mockRejectedValueOnce(error);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useCreateOrganizationQuota('testOrg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.createQuotaMutation({limit_bytes: 1024});
      });
      await waitFor(() => {
        expect(onError).toHaveBeenCalled();
      });
      expect(addDisplayError).toHaveBeenCalledWith(
        'quota creation error',
        error,
      );
      expect(onSuccess).not.toHaveBeenCalled();
    });
  });

  describe('useUpdateOrganizationQuota', () => {
    it('calls resource function and fires onSuccess', async () => {
      vi.mocked(updateOrganizationQuota).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useUpdateOrganizationQuota('testOrg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.updateQuotaMutation({
          quotaId: 'q1',
          params: {limit_bytes: 2048},
        });
      });
      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });
      expect(updateOrganizationQuota).toHaveBeenCalledWith(
        'testOrg',
        'q1',
        {limit_bytes: 2048},
        undefined,
      );
    });

    it('fires onError with addDisplayError on failure', async () => {
      const error = new Error('Update failed');
      vi.mocked(updateOrganizationQuota).mockRejectedValueOnce(error);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useUpdateOrganizationQuota('testOrg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.updateQuotaMutation({
          quotaId: 'q1',
          params: {limit_bytes: 2048},
        });
      });
      await waitFor(() => {
        expect(onError).toHaveBeenCalled();
      });
      expect(addDisplayError).toHaveBeenCalledWith('quota update error', error);
    });
  });

  describe('useDeleteOrganizationQuota', () => {
    it('calls resource function and fires onSuccess', async () => {
      vi.mocked(deleteOrganizationQuota).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useDeleteOrganizationQuota('testOrg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.deleteQuotaMutation('q1');
      });
      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });
      expect(deleteOrganizationQuota).toHaveBeenCalledWith(
        'testOrg',
        'q1',
        undefined,
      );
    });

    it('fires onError with addDisplayError on failure', async () => {
      const error = new Error('Delete failed');
      vi.mocked(deleteOrganizationQuota).mockRejectedValueOnce(error);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useDeleteOrganizationQuota('testOrg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.deleteQuotaMutation('q1');
      });
      await waitFor(() => {
        expect(onError).toHaveBeenCalled();
      });
      expect(addDisplayError).toHaveBeenCalledWith(
        'quota deletion error',
        error,
      );
    });
  });

  describe('useCreateQuotaLimit', () => {
    it('calls resource function and fires onSuccess', async () => {
      vi.mocked(createQuotaLimit).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useCreateQuotaLimit('testOrg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.createLimitMutation({
          quotaId: 'q1',
          params: {type: 'Warning', threshold_percent: 80},
        });
      });
      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });
      expect(createQuotaLimit).toHaveBeenCalledWith('testOrg', 'q1', {
        type: 'Warning',
        threshold_percent: 80,
      });
    });

    it('fires onError with addDisplayError on failure', async () => {
      const error = new Error('Limit creation failed');
      vi.mocked(createQuotaLimit).mockRejectedValueOnce(error);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useCreateQuotaLimit('testOrg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.createLimitMutation({
          quotaId: 'q1',
          params: {type: 'Warning', threshold_percent: 80},
        });
      });
      await waitFor(() => {
        expect(onError).toHaveBeenCalled();
      });
      expect(addDisplayError).toHaveBeenCalledWith(
        'quota limit creation error',
        error,
      );
    });
  });

  describe('useUpdateQuotaLimit', () => {
    it('calls resource function and fires onSuccess', async () => {
      vi.mocked(updateQuotaLimit).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useUpdateQuotaLimit('testOrg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.updateLimitMutation({
          quotaId: 'q1',
          limitId: 'l1',
          params: {type: 'Reject', threshold_percent: 90},
        });
      });
      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });
      expect(updateQuotaLimit).toHaveBeenCalledWith('testOrg', 'q1', 'l1', {
        type: 'Reject',
        threshold_percent: 90,
      });
    });

    it('fires onError with addDisplayError on failure', async () => {
      const error = new Error('Limit update failed');
      vi.mocked(updateQuotaLimit).mockRejectedValueOnce(error);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useUpdateQuotaLimit('testOrg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.updateLimitMutation({
          quotaId: 'q1',
          limitId: 'l1',
          params: {type: 'Reject', threshold_percent: 90},
        });
      });
      await waitFor(() => {
        expect(onError).toHaveBeenCalled();
      });
      expect(addDisplayError).toHaveBeenCalledWith(
        'quota limit update error',
        error,
      );
    });
  });

  describe('useDeleteQuotaLimit', () => {
    it('calls resource function and fires onSuccess', async () => {
      vi.mocked(deleteQuotaLimit).mockResolvedValueOnce(undefined);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useDeleteQuotaLimit('testOrg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.deleteLimitMutation({quotaId: 'q1', limitId: 'l1'});
      });
      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled();
      });
      expect(deleteQuotaLimit).toHaveBeenCalledWith('testOrg', 'q1', 'l1');
    });

    it('fires onError with addDisplayError on failure', async () => {
      const error = new Error('Limit delete failed');
      vi.mocked(deleteQuotaLimit).mockRejectedValueOnce(error);
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useDeleteQuotaLimit('testOrg', {onSuccess, onError}),
        {wrapper},
      );
      act(() => {
        result.current.deleteLimitMutation({quotaId: 'q1', limitId: 'l1'});
      });
      await waitFor(() => {
        expect(onError).toHaveBeenCalled();
      });
      expect(addDisplayError).toHaveBeenCalledWith(
        'quota limit deletion error',
        error,
      );
    });
  });
});
