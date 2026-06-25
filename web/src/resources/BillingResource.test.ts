import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchSubscription,
  setSubscription,
  fetchPlans,
  fetchPrivateAllowed,
  fetchCard,
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
