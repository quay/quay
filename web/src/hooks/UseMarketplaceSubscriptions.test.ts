import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useMarketplaceSubscriptions,
  useManageOrgSubscriptions,
} from './UseMarketplaceSubscriptions';
import {
  fetchMarketplaceSubscriptions,
  setMarketplaceOrgAttachment,
  setMarketplaceOrgRemoval,
} from 'src/resources/BillingResource';

vi.mock('src/resources/BillingResource', () => ({
  fetchMarketplaceSubscriptions: vi.fn(),
  setMarketplaceOrgAttachment: vi.fn(),
  setMarketplaceOrgRemoval: vi.fn(),
}));

vi.mock('./UseCurrentUser', () => ({
  useCurrentUser: vi.fn(() => ({user: {username: 'testuser'}})),
}));

vi.mock('./UseQuayConfig', () => ({
  useQuayConfig: vi.fn(() => ({
    features: {RH_MARKETPLACE: true},
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

describe('UseMarketplaceSubscriptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useMarketplaceSubscriptions', () => {
    it('fetches user subscriptions', async () => {
      const mockUserSubs = [{id: 'sub1', sku: 'premium'}];
      vi.mocked(fetchMarketplaceSubscriptions).mockResolvedValue(
        mockUserSubs as any,
      );

      const {result} = renderHook(
        () => useMarketplaceSubscriptions('testuser', 'testuser'),
        {wrapper},
      );

      await waitFor(() => expect(result.current.loading).toBe(false));
      expect(result.current.userSubscriptions).toEqual(mockUserSubs);
    });

    it('fetches both user and org subscriptions when org differs from user', async () => {
      const mockUserSubs = [{id: 'sub1'}];
      const mockOrgSubs = [{id: 'sub2'}];
      vi.mocked(fetchMarketplaceSubscriptions).mockImplementation(
        (org?: string) => {
          if (org === 'myorg') return Promise.resolve(mockOrgSubs as any);
          return Promise.resolve(mockUserSubs as any);
        },
      );

      const {result} = renderHook(
        () => useMarketplaceSubscriptions('myorg', 'testuser'),
        {wrapper},
      );

      await waitFor(() => expect(result.current.loading).toBe(false));
      expect(result.current.userSubscriptions).toEqual(mockUserSubs);
      expect(result.current.orgSubscriptions).toEqual(mockOrgSubs);
    });
  });

  describe('useManageOrgSubscriptions', () => {
    it('calls setMarketplaceOrgAttachment for attach type', async () => {
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useManageOrgSubscriptions('myorg', {onSuccess, onError}),
        {wrapper},
      );

      act(() => {
        result.current.manageSubscription({
          subscription: {id: 'sub-123'},
          manageType: 'attach',
          bindingQuantity: 5,
        });
      });

      await waitFor(() =>
        expect(result.current.successManageSubscription).toBe(true),
      );
      expect(setMarketplaceOrgAttachment).toHaveBeenCalledWith('myorg', [
        {subscription_id: 'sub-123', quantity: 5},
      ]);
    });

    it('calls setMarketplaceOrgRemoval for remove type', async () => {
      const onSuccess = vi.fn();
      const onError = vi.fn();
      const {result} = renderHook(
        () => useManageOrgSubscriptions('myorg', {onSuccess, onError}),
        {wrapper},
      );

      act(() => {
        result.current.manageSubscription({
          subscription: {subscription_id: 'sub-456'},
          manageType: 'remove',
          bindingQuantity: 0,
        });
      });

      await waitFor(() =>
        expect(result.current.successManageSubscription).toBe(true),
      );
      expect(setMarketplaceOrgRemoval).toHaveBeenCalledWith('myorg', [
        {subscription_id: 'sub-456'},
      ]);
    });
  });
});
