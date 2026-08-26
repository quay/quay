import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useFetchRepositoryAutoPrunePolicies,
  useCreateRepositoryAutoPrunePolicy,
  useUpdateRepositoryAutoPrunePolicy,
  useDeleteRepositoryAutoPrunePolicy,
} from './UseRepositoryAutoPrunePolicies';
import {
  fetchRepositoryAutoPrunePolicies,
  createRepositoryAutoPrunePolicy,
  updateRepositoryAutoPrunePolicy,
  deleteRepositoryAutoPrunePolicy,
} from 'src/resources/RepositoryAutoPruneResource';

vi.mock('src/resources/RepositoryAutoPruneResource', () => ({
  fetchRepositoryAutoPrunePolicies: vi.fn(),
  createRepositoryAutoPrunePolicy: vi.fn(),
  updateRepositoryAutoPrunePolicy: vi.fn(),
  deleteRepositoryAutoPrunePolicy: vi.fn(),
}));

function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

describe('UseRepositoryAutoPrunePolicies', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useFetchRepositoryAutoPrunePolicies', () => {
    it('fetches repo autopruning policies', async () => {
      const mockPolicies = [{uuid: 'p1', method: 'creation_date', value: '7d'}];
      vi.mocked(fetchRepositoryAutoPrunePolicies).mockResolvedValueOnce(
        mockPolicies as any,
      );
      const {result} = renderHook(
        () => useFetchRepositoryAutoPrunePolicies('myorg', 'myrepo'),
        {wrapper},
      );
      await waitFor(() =>
        expect(result.current.successFetchingRepoPolicies).toBe(true),
      );
      expect(result.current.repoPolicies).toEqual(mockPolicies);
    });
  });

  describe('useCreateRepositoryAutoPrunePolicy', () => {
    it('calls createRepositoryAutoPrunePolicy', async () => {
      vi.mocked(createRepositoryAutoPrunePolicy).mockResolvedValueOnce(
        undefined,
      );
      const {result} = renderHook(
        () => useCreateRepositoryAutoPrunePolicy('myorg', 'myrepo'),
        {wrapper},
      );
      const policy = {method: 'number_of_tags', value: 5} as any;
      act(() => {
        result.current.createRepoPolicy(policy);
      });
      await waitFor(() =>
        expect(result.current.successRepoPolicyCreation).toBe(true),
      );
      expect(createRepositoryAutoPrunePolicy).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        policy,
      );
    });
  });

  describe('useUpdateRepositoryAutoPrunePolicy', () => {
    it('calls updateRepositoryAutoPrunePolicy', async () => {
      vi.mocked(updateRepositoryAutoPrunePolicy).mockResolvedValueOnce(
        undefined,
      );
      const {result} = renderHook(
        () => useUpdateRepositoryAutoPrunePolicy('myorg', 'myrepo'),
        {wrapper},
      );
      const policy = {uuid: 'p1', method: 'number_of_tags', value: 20} as any;
      act(() => {
        result.current.updateRepoPolicy(policy);
      });
      await waitFor(() =>
        expect(result.current.successRepoPolicyUpdation).toBe(true),
      );
    });
  });

  describe('useDeleteRepositoryAutoPrunePolicy', () => {
    it('calls deleteRepositoryAutoPrunePolicy with uuid', async () => {
      vi.mocked(deleteRepositoryAutoPrunePolicy).mockResolvedValueOnce(
        undefined,
      );
      const {result} = renderHook(
        () => useDeleteRepositoryAutoPrunePolicy('myorg', 'myrepo'),
        {wrapper},
      );
      act(() => {
        result.current.deleteRepoPolicy('p1');
      });
      await waitFor(() =>
        expect(result.current.successRepoPolicyDeletion).toBe(true),
      );
      expect(deleteRepositoryAutoPrunePolicy).toHaveBeenCalledWith(
        'myorg',
        'myrepo',
        'p1',
      );
    });
  });
});
