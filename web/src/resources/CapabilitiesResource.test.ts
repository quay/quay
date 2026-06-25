import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {fetchRegistryCapabilities} from './CapabilitiesResource';

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

describe('CapabilitiesResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchRegistryCapabilities', () => {
    it('fetches registry capabilities', async () => {
      const caps = {
        sparse_manifests: {
          supported: true,
          required_architectures: ['amd64'],
          optional_architectures_allowed: true,
        },
        mirror_architectures: ['amd64', 'arm64'],
      };
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(caps));

      const result = await fetchRegistryCapabilities();
      expect(axios.get).toHaveBeenCalledWith('/api/v1/registry/capabilities');
      expect(result).toEqual(caps);
    });
  });
});
