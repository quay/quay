import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchServiceKeys,
  createServiceKey,
  deleteServiceKey,
  approveServiceKey,
} from './ServiceKeysResource';

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

describe('ServiceKeysResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchServiceKeys', () => {
    it('fetches service keys', async () => {
      const keys = [{kid: 'k1', service: 'quay'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({keys}));

      const result = await fetchServiceKeys();
      expect(axios.get).toHaveBeenCalledWith('/api/v1/superuser/keys');
      expect(result).toEqual(keys);
    });
  });

  describe('createServiceKey', () => {
    it('creates a service key', async () => {
      const key = {kid: 'k1', service: 'quay'};
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(key));

      const result = await createServiceKey({
        service: 'quay',
        expiration: null,
      });
      expect(axios.post).toHaveBeenCalledWith('/api/v1/superuser/keys', {
        service: 'quay',
        expiration: null,
      });
      expect(result).toEqual(key);
    });
  });

  describe('deleteServiceKey', () => {
    it('deletes a service key', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteServiceKey('k1');
      expect(axios.delete).toHaveBeenCalledWith('/api/v1/superuser/keys/k1');
    });
  });

  describe('approveServiceKey', () => {
    it('approves a service key', async () => {
      const key = {kid: 'k1', service: 'quay'};
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(key));

      const result = await approveServiceKey('k1');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/superuser/approvedkeys/k1',
      );
      expect(result).toEqual(key);
    });
  });
});
