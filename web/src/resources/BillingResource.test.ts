import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchSubscription,
  setSubscription,
  fetchPlans,
  fetchPrivateAllowed,
  fetchCard,
  createCardSetupSession,
  createSubscriptionCheckoutSession,
  setMarketplaceOrgAttachment,
  setMarketplaceOrgRemoval,
} from './BillingResource';
import {ResourceError} from './ErrorHandling';

vi.mock('src/libs/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

/** Creates a mock Axios response with the given data and status. */
function mockResponse(data: unknown, status = 200): AxiosResponse {
  return {
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: {} as InternalAxiosRequestConfig,
  };
}

describe('BillingResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchSubscription', () => {
    it('uses user endpoint when no org provided', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({plan: 'free'}));

      await fetchSubscription();
      expect(axios.get).toHaveBeenCalledWith('/api/v1/user/plan');
    });

    it('uses org endpoint when org provided', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({plan: 'team'}));

      await fetchSubscription('myorg');
      expect(axios.get).toHaveBeenCalledWith('/api/v1/organization/myorg/plan');
    });
  });

  describe('setSubscription', () => {
    it('sets subscription with plan only', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await setSubscription('pro');
      expect(axios.put).toHaveBeenCalledWith('/api/v1/user/plan', {
        plan: 'pro',
      });
    });

    it('includes token when provided', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await setSubscription('pro', 'myorg', 'stripe_tok');
      expect(vi.mocked(axios.put).mock.calls[0][1]).toEqual({
        plan: 'pro',
        token: 'stripe_tok',
      });
    });
  });

  describe('fetchPlans', () => {
    it('fetches available plans', async () => {
      const plans = [{title: 'Free', price: 0}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({plans}));

      const result = await fetchPlans();
      expect(axios.get).toHaveBeenCalledWith('/api/v1/plans/');
      expect(result).toEqual(plans);
    });
  });

  describe('fetchPrivateAllowed', () => {
    it('uses user endpoint when no org', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({privateAllowed: true, privateCount: 5}),
      );

      const result = await fetchPrivateAllowed();
      expect(axios.get).toHaveBeenCalledWith('/api/v1/user/private');
      expect(result.privateAllowed).toBe(true);
    });
  });

  describe('fetchCard', () => {
    it('fetches card info', async () => {
      const card = {last4: '1234', type: 'visa'};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({card}));

      const result = await fetchCard();
      expect(result).toEqual(card);
    });
  });

  describe('createCardSetupSession', () => {
    const returnUrls = {
      success_url:
        'http://localhost:9010/organization/user1?tab=Settings&settingsTab=billinginformation&paymentMethod=returned',
      cancel_url:
        'http://localhost:9010/organization/user1?tab=Settings&settingsTab=billinginformation&paymentMethod=canceled',
    };

    it.each([null, 'myorg'])(
      'starts the existing Stripe card setup flow for %s',
      async (org) => {
        const session = {
          url: 'https://checkout.stripe.com/c/pay/cs_test_sample',
        };
        vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(session));
        expect(await createCardSetupSession(returnUrls, org)).toEqual(session);
        expect(axios.post).toHaveBeenCalledWith(
          org ? `/api/v1/organization/${org}/card` : '/api/v1/user/card',
          returnUrls,
        );
      },
    );

    it('rejects an incomplete checkout response', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));
      await expect(createCardSetupSession(returnUrls)).rejects.toThrow(
        'Stripe did not return a checkout URL',
      );
    });

    it('passes checkout failures back to the UI', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(
        new AxiosError('Cannot contact Stripe'),
      );
      await expect(createCardSetupSession(returnUrls)).rejects.toThrow(
        'Cannot contact Stripe',
      );
    });
  });

  describe('createSubscriptionCheckoutSession', () => {
    const returnUrls = {
      success_url:
        'http://localhost:9010/organization/user1?tab=Settings&settingsTab=billinginformation',
      cancel_url: 'http://localhost:9010/organization/user1/plans',
    };
    it.each([null, 'projectquay'])(
      'includes the selected plan in the Stripe checkout request for %s',
      async (org) => {
        const session = {
          url: 'https://checkout.stripe.com/c/pay/cs_test_sample',
        };
        vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(session));
        expect(
          await createSubscriptionCheckoutSession(
            'bus-small-2018',
            returnUrls,
            org,
          ),
        ).toEqual(session);
        expect(axios.post).toHaveBeenCalledWith(
          org ? `/api/v1/organization/${org}/plan` : '/api/v1/user/plan',
          {plan: 'bus-small-2018', ...returnUrls},
        );
      },
    );
    it('rejects a response with no checkout URL', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));
      await expect(
        createSubscriptionCheckoutSession('bus-small-2018', returnUrls),
      ).rejects.toThrow('Stripe did not return a checkout URL');
    });
  });

  describe('setMarketplaceOrgAttachment', () => {
    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        setMarketplaceOrgAttachment('myorg', [{id: '1'}]),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('setMarketplaceOrgRemoval', () => {
    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        setMarketplaceOrgRemoval('myorg', [{id: '1'}]),
      ).rejects.toThrow(ResourceError);
    });
  });
});
