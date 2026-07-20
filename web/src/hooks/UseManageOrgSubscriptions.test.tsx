import React from 'react';
import {renderHook, act, waitFor} from '@testing-library/react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useManageOrgSubscriptions} from './UseMarketplaceSubscriptions';
import {
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

describe('useManageOrgSubscriptions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should await attachment API call before resolving', async () => {
    const callOrder: string[] = [];
    let resolveAttachment: () => void;
    const attachmentPromise = new Promise<void>((resolve) => {
      resolveAttachment = resolve;
    });

    vi.mocked(setMarketplaceOrgAttachment).mockImplementation(async () => {
      await attachmentPromise;
      callOrder.push('api_complete');
    });

    const onSuccess = vi.fn(() => callOrder.push('onSuccess'));
    const onError = vi.fn();

    const {result} = renderHook(
      () => useManageOrgSubscriptions('myorg', {onSuccess, onError}),
      {wrapper},
    );

    act(() => {
      result.current.manageSubscription({
        subscription: {id: 'sub-123'},
        manageType: 'attach',
        bindingQuantity: 1,
      });
    });

    expect(onSuccess).not.toHaveBeenCalled();

    resolveAttachment!();

    await waitFor(() =>
      expect(result.current.successManageSubscription).toBe(true),
    );
    expect(onSuccess).toHaveBeenCalled();
    expect(callOrder).toEqual(['api_complete', 'onSuccess']);
  });

  it('should call onError when attachment API fails', async () => {
    vi.mocked(setMarketplaceOrgAttachment).mockRejectedValue(
      new Error('Attach failed'),
    );

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
        bindingQuantity: 1,
      });
    });

    await waitFor(() =>
      expect(result.current.errorManageSubscription).toBe(true),
    );
    expect(onError).toHaveBeenCalled();
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it('should await removal API call before resolving', async () => {
    const callOrder: string[] = [];
    let resolveRemoval: () => void;
    const removalPromise = new Promise<void>((resolve) => {
      resolveRemoval = resolve;
    });

    vi.mocked(setMarketplaceOrgRemoval).mockImplementation(async () => {
      await removalPromise;
      callOrder.push('api_complete');
    });

    const onSuccess = vi.fn(() => callOrder.push('onSuccess'));
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

    expect(onSuccess).not.toHaveBeenCalled();

    resolveRemoval!();

    await waitFor(() =>
      expect(result.current.successManageSubscription).toBe(true),
    );
    expect(onSuccess).toHaveBeenCalled();
    expect(callOrder).toEqual(['api_complete', 'onSuccess']);
  });

  it('should call onError when removal API fails', async () => {
    vi.mocked(setMarketplaceOrgRemoval).mockRejectedValue(
      new Error('Remove failed'),
    );

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
      expect(result.current.errorManageSubscription).toBe(true),
    );
    expect(onError).toHaveBeenCalled();
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it('should pass correct subscription_id for attach vs remove', async () => {
    vi.mocked(setMarketplaceOrgAttachment).mockResolvedValue(undefined);
    vi.mocked(setMarketplaceOrgRemoval).mockResolvedValue(undefined);

    const onSuccess = vi.fn();
    const onError = vi.fn();

    const {result: attachResult} = renderHook(
      () => useManageOrgSubscriptions('myorg', {onSuccess, onError}),
      {wrapper},
    );

    act(() => {
      attachResult.current.manageSubscription({
        subscription: {id: 'user-sub-100'},
        manageType: 'attach',
        bindingQuantity: 3,
      });
    });

    await waitFor(() =>
      expect(attachResult.current.successManageSubscription).toBe(true),
    );
    expect(setMarketplaceOrgAttachment).toHaveBeenCalledWith('myorg', [
      {subscription_id: 'user-sub-100', quantity: 3},
    ]);

    const {result: removeResult} = renderHook(
      () => useManageOrgSubscriptions('myorg', {onSuccess, onError}),
      {wrapper},
    );

    act(() => {
      removeResult.current.manageSubscription({
        subscription: {subscription_id: 'org-sub-200'},
        manageType: 'remove',
        bindingQuantity: 0,
      });
    });

    await waitFor(() =>
      expect(removeResult.current.successManageSubscription).toBe(true),
    );
    expect(setMarketplaceOrgRemoval).toHaveBeenCalledWith('myorg', [
      {subscription_id: 'org-sub-200'},
    ]);
  });
});
