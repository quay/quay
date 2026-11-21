import React, {ReactNode} from 'react';
import {renderHook, waitFor} from '@testing-library/react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {useMarketplaceSubscriptions} from './UseMarketplaceSubscriptions';
import * as BillingResource from 'src/resources/BillingResource';

jest.mock('src/resources/BillingResource', () => ({
  ...jest.requireActual('src/resources/BillingResource'),
  fetchMarketplaceSubscriptions: jest.fn(),
}));

jest.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: jest.fn(() => ({features: {RH_MARKETPLACE: true}})),
}));

jest.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: jest.fn(() => ({user: {username: 'testuser'}})),
}));

import {useQuayConfig} from 'src/hooks/UseQuayConfig';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
      },
    },
  });

  const Wrapper = ({children}: {children: ReactNode}) => {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };

  return Wrapper;
};

describe('useMarketplaceSubscriptions', () => {
  const mockFetchMarketplaceSubscriptions =
    BillingResource.fetchMarketplaceSubscriptions as jest.Mock;
  const mockUseQuayConfig = useQuayConfig as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseQuayConfig.mockReturnValue({features: {RH_MARKETPLACE: true}});
  });

  it('should include organizationName in org query key (fetches different data per org)', async () => {
    const orgAData = {subscriptions: [{id: '1', org: 'orgA'}]};
    const orgBData = {subscriptions: [{id: '2', org: 'orgB'}]};

    mockFetchMarketplaceSubscriptions.mockImplementation((org?: string) => {
      if (org === 'orgA') return Promise.resolve(orgAData);
      if (org === 'orgB') return Promise.resolve(orgBData);
      return Promise.resolve({subscriptions: []});
    });

    const {result: resultA} = renderHook(
      () => useMarketplaceSubscriptions('orgA', 'testuser'),
      {wrapper: createWrapper()},
    );

    await waitFor(() => {
      expect(resultA.current.loading).toBe(false);
    });

    expect(mockFetchMarketplaceSubscriptions).toHaveBeenCalledWith('orgA');
    expect(resultA.current.orgSubscriptions).toEqual(orgAData);

    const {result: resultB} = renderHook(
      () => useMarketplaceSubscriptions('orgB', 'testuser'),
      {wrapper: createWrapper()},
    );

    await waitFor(() => {
      expect(resultB.current.loading).toBe(false);
    });

    expect(mockFetchMarketplaceSubscriptions).toHaveBeenCalledWith('orgB');
    expect(resultB.current.orgSubscriptions).toEqual(orgBData);
  });

  it('should not fetch org subscriptions when org equals user', async () => {
    mockFetchMarketplaceSubscriptions.mockResolvedValue({subscriptions: []});

    const {result} = renderHook(
      () => useMarketplaceSubscriptions('testuser', 'testuser'),
      {wrapper: createWrapper()},
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const orgCalls = mockFetchMarketplaceSubscriptions.mock.calls.filter(
      (call) => call[0] === 'testuser',
    );
    expect(orgCalls).toHaveLength(0);
    expect(result.current.orgSubscriptions).toBeUndefined();
  });

  it('should not fetch when RH_MARKETPLACE is disabled', async () => {
    mockUseQuayConfig.mockReturnValue({features: {RH_MARKETPLACE: false}});
    mockFetchMarketplaceSubscriptions.mockResolvedValue({subscriptions: []});

    renderHook(
      () => useMarketplaceSubscriptions('orgA', 'testuser'),
      {wrapper: createWrapper()},
    );

    await new Promise((r) => setTimeout(r, 50));

    expect(mockFetchMarketplaceSubscriptions).not.toHaveBeenCalled();
  });

  it('should return user and org subscriptions on success', async () => {
    const userSubs = {subscriptions: [{id: 'u1', plan: 'pro'}]};
    const orgSubs = {subscriptions: [{id: 'o1', plan: 'team'}]};

    mockFetchMarketplaceSubscriptions.mockImplementation((org?: string) => {
      if (org) return Promise.resolve(orgSubs);
      return Promise.resolve(userSubs);
    });

    const {result} = renderHook(
      () => useMarketplaceSubscriptions('myorg', 'testuser'),
      {wrapper: createWrapper()},
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.userSubscriptions).toEqual(userSubs);
    expect(result.current.orgSubscriptions).toEqual(orgSubs);
    expect(result.current.error).toBeFalsy();
  });
});
