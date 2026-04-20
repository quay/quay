import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchOAuthApplications,
  updateOAuthApplication,
  createOAuthApplication,
  resetOAuthApplicationClientSecret,
} from './OAuthApplicationResource';
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

describe('OAuthApplicationResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchOAuthApplications', () => {
    it('fetches applications for an org', async () => {
      const applications = [{client_id: 'c1', name: 'app1'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({applications}));

      const result = await fetchOAuthApplications('myorg');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/applications',
      );
      expect(result).toEqual(applications);
    });
  });

  describe('updateOAuthApplication', () => {
    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.put).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        updateOAuthApplication('myorg', 'c1', {name: 'new'}),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('createOAuthApplication', () => {
    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        createOAuthApplication('myorg', {name: 'app'} as any),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('resetOAuthApplicationClientSecret', () => {
    it('resets client secret', async () => {
      const app = {client_id: 'c1', client_secret: 'new_secret'};
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(app));

      const result = await resetOAuthApplicationClientSecret('myorg', 'c1');
      expect(vi.mocked(axios.post).mock.calls[0][0]).toContain(
        'resetclientsecret',
      );
      expect(result).toEqual(app);
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        resetOAuthApplicationClientSecret('myorg', 'c1'),
      ).rejects.toThrow(ResourceError);
    });
  });
});
