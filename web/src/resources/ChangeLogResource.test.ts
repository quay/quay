import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {fetchChangeLog} from './ChangeLogResource';

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

describe('ChangeLogResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchChangeLog', () => {
    it('fetches the changelog', async () => {
      const data = {log: '## v1.0.0\n- Initial release'};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(data));

      const result = await fetchChangeLog();
      expect(axios.get).toHaveBeenCalledWith('/api/v1/superuser/changelog/');
      expect(result).toEqual(data);
    });
  });
});
