import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchGlobalMessages,
  createGlobalMessage,
  deleteGlobalMessage,
} from './GlobalMessagesResource';

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

describe('GlobalMessagesResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchGlobalMessages', () => {
    it('returns messages array', async () => {
      const messages = [{uuid: 'm1', content: 'Maintenance window'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({messages}));

      const result = await fetchGlobalMessages();
      expect(axios.get).toHaveBeenCalledWith('/api/v1/messages');
      expect(result).toEqual(messages);
    });

    it('returns empty array when messages is missing', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({}));

      const result = await fetchGlobalMessages();
      expect(result).toEqual([]);
    });
  });

  describe('createGlobalMessage', () => {
    it('creates a global message', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}, 201));

      await createGlobalMessage({
        message: {content: 'test', media_type: 'text/plain', severity: 'info'},
      });
      expect(axios.post).toHaveBeenCalledWith('/api/v1/messages', {
        message: {content: 'test', media_type: 'text/plain', severity: 'info'},
      });
    });
  });

  describe('deleteGlobalMessage', () => {
    it('deletes a global message by uuid', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteGlobalMessage('msg-uuid');
      expect(axios.delete).toHaveBeenCalledWith('/api/v1/message/msg-uuid');
    });
  });
});
