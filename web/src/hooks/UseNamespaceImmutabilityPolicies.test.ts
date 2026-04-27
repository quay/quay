import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useNamespaceImmutabilityPolicies,
  useCreateNamespaceImmutabilityPolicy,
  useUpdateNamespaceImmutabilityPolicy,
  useDeleteNamespaceImmutabilityPolicy,
} from './UseNamespaceImmutabilityPolicies';
import {
  fetchNamespaceImmutabilityPolicies,
  createNamespaceImmutabilityPolicy,
  updateNamespaceImmutabilityPolicy,
  deleteNamespaceImmutabilityPolicy,
} from 'src/resources/ImmutabilityPolicyResource';

vi.mock('src/resources/ImmutabilityPolicyResource', () => ({
  fetchNamespaceImmutabilityPolicies: vi.fn(),
  createNamespaceImmutabilityPolicy: vi.fn(),
  updateNamespaceImmutabilityPolicy: vi.fn(),
  deleteNamespaceImmutabilityPolicy: vi.fn(),
  fetchRepositoryImmutabilityPolicies: vi.fn(),
  createRepositoryImmutabilityPolicy: vi.fn(),
  updateRepositoryImmutabilityPolicy: vi.fn(),
  deleteRepositoryImmutabilityPolicy: vi.fn(),
}));

function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

describe('UseNamespaceImmutabilityPolicies', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useNamespaceImmutabilityPolicies', () => {
    it('fetches namespace immutability policies', async () => {
      const mockPolicies = [
        {uuid: 'u1', tag_pattern: 'v.*', match_type: 'glob'},
      ];
      vi.mocked(fetchNamespaceImmutabilityPolicies).mockResolvedValueOnce(
        mockPolicies as any,
      );
      const {result} = renderHook(
        () => useNamespaceImmutabilityPolicies('myorg'),
        {wrapper},
      );
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.nsPolicies).toEqual(mockPolicies);
    });

    it('does not fetch when isEnabled=false', () => {
      const {result} = renderHook(
        () => useNamespaceImmutabilityPolicies('myorg', false),
        {wrapper},
      );
      expect(fetchNamespaceImmutabilityPolicies).not.toHaveBeenCalled();
      expect(result.current.isLoading).toBe(true);
    });
  });

  describe('useCreateNamespaceImmutabilityPolicy', () => {
    it('calls createNamespaceImmutabilityPolicy and fires onSuccess', async () => {
      vi.mocked(createNamespaceImmutabilityPolicy).mockResolvedValueOnce(
        undefined,
      );
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () =>
          useCreateNamespaceImmutabilityPolicy('myorg', {onSuccess, onError}),
        {wrapper},
      );
      const policy = {tag_pattern: 'v.*', match_type: 'glob'} as any;
      act(() => {
        result.current.createPolicy(policy);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(createNamespaceImmutabilityPolicy).toHaveBeenCalledWith(
        'myorg',
        policy,
      );
    });
  });

  describe('useUpdateNamespaceImmutabilityPolicy', () => {
    it('calls updateNamespaceImmutabilityPolicy and fires onSuccess', async () => {
      vi.mocked(updateNamespaceImmutabilityPolicy).mockResolvedValueOnce(
        undefined,
      );
      const onSuccess = vi.fn();
      const {result} = renderHook(
        () => useUpdateNamespaceImmutabilityPolicy('myorg', {onSuccess}),
        {wrapper},
      );
      const policy = {
        uuid: 'u1',
        tag_pattern: 'v1.*',
        match_type: 'glob',
      } as any;
      act(() => {
        result.current.updatePolicy(policy);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(updateNamespaceImmutabilityPolicy).toHaveBeenCalledWith(
        'myorg',
        policy,
      );
    });
  });

  describe('useDeleteNamespaceImmutabilityPolicy', () => {
    it('calls deleteNamespaceImmutabilityPolicy with uuid and fires onSuccess', async () => {
      vi.mocked(deleteNamespaceImmutabilityPolicy).mockResolvedValueOnce(
        undefined,
      );
      const onSuccess = vi.fn();
      const {result} = renderHook(
        () => useDeleteNamespaceImmutabilityPolicy('myorg', {onSuccess}),
        {wrapper},
      );
      act(() => {
        result.current.deletePolicy('u1');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(deleteNamespaceImmutabilityPolicy).toHaveBeenCalledWith(
        'myorg',
        'u1',
      );
    });
  });
});
