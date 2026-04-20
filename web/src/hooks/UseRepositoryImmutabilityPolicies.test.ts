import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useFetchRepositoryImmutabilityPolicies,
  useCreateRepositoryImmutabilityPolicy,
  useUpdateRepositoryImmutabilityPolicy,
  useDeleteRepositoryImmutabilityPolicy,
} from './UseRepositoryImmutabilityPolicies';
import {
  fetchRepositoryImmutabilityPolicies,
  createRepositoryImmutabilityPolicy,
  updateRepositoryImmutabilityPolicy,
  deleteRepositoryImmutabilityPolicy,
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

describe('UseRepositoryImmutabilityPolicies', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useFetchRepositoryImmutabilityPolicies', () => {
    it('fetches repo immutability policies', async () => {
      const mockPolicies = [
        {uuid: 'u1', tag_pattern: 'v.*', match_type: 'glob'},
      ];
      vi.mocked(fetchRepositoryImmutabilityPolicies).mockResolvedValueOnce(
        mockPolicies as any,
      );
      const {result} = renderHook(
        () => useFetchRepositoryImmutabilityPolicies('myorg', 'myrepo'),
        {wrapper},
      );
      await waitFor(() =>
        expect(result.current.successFetchingRepoPolicies).toBe(true),
      );
      expect(result.current.repoPolicies).toEqual(mockPolicies);
    });
  });

  describe('useCreateRepositoryImmutabilityPolicy', () => {
    it('calls createRepositoryImmutabilityPolicy and fires onSuccess', async () => {
      vi.mocked(createRepositoryImmutabilityPolicy).mockResolvedValueOnce(
        undefined,
      );
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () =>
          useCreateRepositoryImmutabilityPolicy('myorg', 'myrepo', {
            onSuccess,
            onError,
          }),
        {wrapper},
      );
      const policy = {tag_pattern: 'v.*', match_type: 'glob'} as any;
      act(() => {
        result.current.createRepoPolicy(policy);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(createRepositoryImmutabilityPolicy).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        policy,
      );
    });
  });

  describe('useUpdateRepositoryImmutabilityPolicy', () => {
    it('calls updateRepositoryImmutabilityPolicy and fires onSuccess', async () => {
      vi.mocked(updateRepositoryImmutabilityPolicy).mockResolvedValueOnce(
        undefined,
      );
      const onSuccess = vi.fn();
      const {result} = renderHook(
        () =>
          useUpdateRepositoryImmutabilityPolicy('myorg', 'myrepo', {
            onSuccess,
          }),
        {wrapper},
      );
      const policy = {
        uuid: 'u1',
        tag_pattern: 'v1.*',
        match_type: 'glob',
      } as any;
      act(() => {
        result.current.updateRepoPolicy(policy);
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    });
  });

  describe('useDeleteRepositoryImmutabilityPolicy', () => {
    it('calls deleteRepositoryImmutabilityPolicy with uuid and fires onSuccess', async () => {
      vi.mocked(deleteRepositoryImmutabilityPolicy).mockResolvedValueOnce(
        undefined,
      );
      const onSuccess = vi.fn();
      const {result} = renderHook(
        () =>
          useDeleteRepositoryImmutabilityPolicy('myorg', 'myrepo', {
            onSuccess,
          }),
        {wrapper},
      );
      act(() => {
        result.current.deleteRepoPolicy('u1');
      });
      await waitFor(() => expect(onSuccess).toHaveBeenCalled());
      expect(deleteRepositoryImmutabilityPolicy).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        'u1',
      );
    });
  });
});
