import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {fetchQuayConfig} from './QuayConfig';

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

describe('QuayConfig', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchQuayConfig', () => {
    it('fetches quay configuration', async () => {
      const config = {features: {BUILD_SUPPORT: true}};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(config));

      const result = await fetchQuayConfig();
      expect(axios.get).toHaveBeenCalledWith('/config');
      expect(result).toEqual(config);
    });
  });
});
