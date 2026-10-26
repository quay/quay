import {renderHook, act, waitFor} from '@testing-library/react';
import {TestWrapper} from 'src/test-utils';
import {
  useMarketplaceSubscriptions,
  useManageOrgSubscriptions,
} from './UseMarketplaceSubscriptions';
import {
  fetchMarketplaceSubscriptions,
  setMarketplaceOrgAttachment,
  setMarketplaceOrgRemoval,
} from 'src/resources/BillingResource';
import {useQuayConfig} from './UseQuayConfig';

vi.mock('src/resources/BillingResource', () => ({
  fetchMarketplaceSubscriptions: vi.fn(),
  setMarketplaceOrgAttachment: vi.fn(),
  setMarketplaceOrgRemoval: vi.fn(),
}));

vi.mock('./UseCurrentUser', () => ({
  useCurrentUser: vi.fn(() => ({user: {username: 'testuser'}})),
}));

vi.mock('./UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

describe('UseMarketplaceSubscriptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useQuayConfig).mockReturnValue({
      features: {RH_MARKETPLACE: true},
    } as ReturnType<typeof useQuayConfig>);
  });

  describe('useMarketplaceSubscriptions', () => {
    it('fetches user subscriptions', async () => {
      const mockUserSubs = [{id: 'sub1', sku: 'premium'}];
      vi.mocked(fetchMarketplaceSubscriptions).mockResolvedValue(
        mockUserSubs as any,
      );

      const {result} = renderHook(
        () => useMarketplaceSubscriptions('testuser', 'testuser'),
        {wrapper: TestWrapper},
      );

      await waitFor(() => expect(result.current.loading).toBe(false));
      expect(result.current.userSubscriptions).toEqual(mockUserSubs);
    });

    it('returns empty subscription lists when marketplace is disabled', () => {
      vi.mocked(useQuayConfig).mockReturnValue({
        features: {RH_MARKETPLACE: false},
      } as ReturnType<typeof useQuayConfig>);

      const {result, rerender} = renderHook(
        () => useMarketplaceSubscriptions('myorg', 'testuser'),
        {wrapper: TestWrapper},
      );
      const initialUserSubscriptions = result.current.userSubscriptions;
      const initialOrgSubscriptions = result.current.orgSubscriptions;

      rerender();

      expect(result.current.userSubscriptions).toEqual([]);
      expect(result.current.orgSubscriptions).toEqual([]);
      expect(result.current.userSubscriptions).toBe(initialUserSubscriptions);
      expect(result.current.orgSubscriptions).toBe(initialOrgSubscriptions);
      expect(fetchMarketplaceSubscriptions).not.toHaveBeenCalled();
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
        {wrapper: TestWrapper},
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
        {wrapper: TestWrapper},
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
        {wrapper: TestWrapper},
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
