import React from 'react';
import {render, screen, waitFor} from 'src/test-utils';
import MarketplaceDetails from './MarketplaceDetails';
import {
  useMarketplaceSubscriptions,
  useManageOrgSubscriptions,
} from 'src/hooks/UseMarketplaceSubscriptions';

vi.mock('src/hooks/UseMarketplaceSubscriptions', () => ({
  useMarketplaceSubscriptions: vi.fn(),
  useManageOrgSubscriptions: vi.fn(),
}));

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: vi.fn(() => ({user: {username: 'testuser'}})),
}));

const mockOrgSubscriptions = [
  {id: '1', sku: 'SKU-A', quantity: 2, metadata: {privateRepos: 5}},
  {id: '2', sku: 'SKU-B', quantity: 1, metadata: {privateRepos: 10}},
];

const mockUserSubscriptions = [
  {
    id: '3',
    sku: 'SKU-C',
    quantity: 3,
    metadata: {privateRepos: 2},
    assigned_to_org: null,
  },
  {
    id: '4',
    sku: 'SKU-D',
    quantity: 1,
    metadata: {privateRepos: 4},
    assigned_to_org: 'some-org',
  },
];

describe('MarketplaceDetails', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useManageOrgSubscriptions).mockReturnValue({
      manageSubscription: vi.fn(),
      errorManageSubscription: false,
      successManageSubscription: false,
    } as any);
  });

  it('should call updateTotalPrivate with correct sum for org subscriptions', async () => {
    vi.mocked(useMarketplaceSubscriptions).mockReturnValue({
      userSubscriptions: [],
      orgSubscriptions: mockOrgSubscriptions,
      loading: false,
      error: null,
    } as any);

    const updateTotalPrivate = vi.fn();
    render(
      <MarketplaceDetails
        organizationName="myorg"
        updateTotalPrivate={updateTotalPrivate}
      />,
    );

    await waitFor(() => {
      expect(updateTotalPrivate).toHaveBeenCalledWith(20);
    });
  });

  it('should not call updateTotalPrivate while loading', () => {
    vi.mocked(useMarketplaceSubscriptions).mockReturnValue({
      userSubscriptions: undefined,
      orgSubscriptions: undefined,
      loading: true,
      error: null,
    } as any);

    const updateTotalPrivate = vi.fn();
    render(
      <MarketplaceDetails
        organizationName="myorg"
        updateTotalPrivate={updateTotalPrivate}
      />,
    );

    expect(updateTotalPrivate).not.toHaveBeenCalled();
  });

  it('should not re-call updateTotalPrivate if subscription data has not changed', async () => {
    vi.mocked(useMarketplaceSubscriptions).mockReturnValue({
      userSubscriptions: mockUserSubscriptions,
      orgSubscriptions: mockOrgSubscriptions,
      loading: false,
      error: null,
    } as any);

    const updateTotalPrivate = vi.fn();
    const {rerender} = render(
      <MarketplaceDetails
        organizationName="myorg"
        updateTotalPrivate={updateTotalPrivate}
      />,
    );

    await waitFor(() => {
      expect(updateTotalPrivate).toHaveBeenCalledTimes(1);
    });

    updateTotalPrivate.mockClear();

    rerender(
      <MarketplaceDetails
        organizationName="myorg"
        updateTotalPrivate={updateTotalPrivate}
      />,
    );

    expect(updateTotalPrivate).not.toHaveBeenCalled();
  });
});
