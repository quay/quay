import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchProxyCacheConfig,
  createProxyCacheConfig,
} from './ProxyCacheResource';

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

describe('ProxyCacheResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchProxyCacheConfig', () => {
    it('fetches proxy cache config for an org', async () => {
      const config = {upstream_registry: 'docker.io'};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(config));

      const result = await fetchProxyCacheConfig('myorg');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/proxycache',
        {signal: undefined},
      );
      expect(result).toEqual(config);
    });
  });

  describe('createProxyCacheConfig', () => {
    it('normalizes null values for empty credentials', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}, 201));

      await createProxyCacheConfig({
        org_name: 'myorg',
        upstream_registry: 'docker.io',
        upstream_registry_username: '',
        upstream_registry_password: '',
      } as any);

      const sentBody = vi.mocked(axios.post).mock.calls[0][1];
      expect(sentBody.upstream_registry_username).toBeNull();
      expect(sentBody.upstream_registry_password).toBeNull();
    });
  });
});
