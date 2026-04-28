import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useNamespaceAutoPrunePolicies,
  useCreateNamespaceAutoPrunePolicy,
  useUpdateNamespaceAutoPrunePolicy,
  useDeleteNamespaceAutoPrunePolicy,
} from './UseNamespaceAutoPrunePolicies';
import {
  fetchNamespaceAutoPrunePolicies,
  createNamespaceAutoPrunePolicy,
  updateNamespaceAutoPrunePolicy,
  deleteNamespaceAutoPrunePolicy,
} from 'src/resources/NamespaceAutoPruneResource';

vi.mock('src/resources/NamespaceAutoPruneResource', () => ({
  fetchNamespaceAutoPrunePolicies: vi.fn(),
  createNamespaceAutoPrunePolicy: vi.fn(),
  updateNamespaceAutoPrunePolicy: vi.fn(),
  deleteNamespaceAutoPrunePolicy: vi.fn(),
}));

function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

describe('UseNamespaceAutoPrunePolicies', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useNamespaceAutoPrunePolicies', () => {
    it('fetches namespace autopruning policies', async () => {
      const mockPolicies = [{uuid: 'p1', method: 'number_of_tags', value: 10}];
      vi.mocked(fetchNamespaceAutoPrunePolicies).mockResolvedValueOnce(
        mockPolicies as any,
      );
      const {result} = renderHook(
        () => useNamespaceAutoPrunePolicies('myorg', false),
        {wrapper},
      );
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.nsPolicies).toEqual(mockPolicies);
    });

    it('does not fetch when isEnabled=false', () => {
      const {result} = renderHook(
        () => useNamespaceAutoPrunePolicies('myorg', false, false),
        {wrapper},
      );
      expect(fetchNamespaceAutoPrunePolicies).not.toHaveBeenCalled();
      expect(result.current.isLoading).toBe(true);
    });
  });

  describe('useCreateNamespaceAutoPrunePolicy', () => {
    it('calls createNamespaceAutoPrunePolicy', async () => {
      vi.mocked(createNamespaceAutoPrunePolicy).mockResolvedValueOnce(
        undefined,
      );
      const {result} = renderHook(
        () => useCreateNamespaceAutoPrunePolicy('myorg', false),
        {wrapper},
      );
      const policy = {method: 'number_of_tags', value: 5} as any;
      act(() => {
        result.current.createPolicy(policy);
      });
      await waitFor(() =>
        expect(result.current.successCreatePolicy).toBe(true),
      );
      expect(createNamespaceAutoPrunePolicy).toHaveBeenCalledWith(
        'myorg',
        policy,
        false,
      );
    });
  });

  describe('useUpdateNamespaceAutoPrunePolicy', () => {
    it('calls updateNamespaceAutoPrunePolicy', async () => {
      vi.mocked(updateNamespaceAutoPrunePolicy).mockResolvedValueOnce(
        undefined,
      );
      const {result} = renderHook(
        () => useUpdateNamespaceAutoPrunePolicy('myorg', false),
        {wrapper},
      );
      const policy = {uuid: 'p1', method: 'number_of_tags', value: 20} as any;
      act(() => {
        result.current.updatePolicy(policy);
      });
      await waitFor(() =>
        expect(result.current.successUpdatePolicy).toBe(true),
      );
    });
  });

  describe('useDeleteNamespaceAutoPrunePolicy', () => {
    it('calls deleteNamespaceAutoPrunePolicy with uuid', async () => {
      vi.mocked(deleteNamespaceAutoPrunePolicy).mockResolvedValueOnce(
        undefined,
      );
      const {result} = renderHook(
        () => useDeleteNamespaceAutoPrunePolicy('myorg', false),
        {wrapper},
      );
      act(() => {
        result.current.deletePolicy('p1');
      });
      await waitFor(() =>
        expect(result.current.successDeletePolicy).toBe(true),
      );
      expect(deleteNamespaceAutoPrunePolicy).toHaveBeenCalledWith(
        'myorg',
        'p1',
        false,
      );
    });
  });
});
