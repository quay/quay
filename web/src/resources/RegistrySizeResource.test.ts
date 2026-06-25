import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchRegistrySize,
  queueRegistrySizeCalculation,
} from './RegistrySizeResource';

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

describe('RegistrySizeResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchRegistrySize', () => {
    it('fetches registry size data', async () => {
      const data = {
        size_bytes: 1024,
        last_ran: 1700000000,
        queued: false,
        running: false,
      };
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(data));

      const result = await fetchRegistrySize();
      expect(axios.get).toHaveBeenCalledWith('/api/v1/superuser/registrysize/');
      expect(result).toEqual(data);
    });
  });

  describe('queueRegistrySizeCalculation', () => {
    it('queues size calculation', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await queueRegistrySizeCalculation();
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/superuser/registrysize/',
      );
    });
  });
});
