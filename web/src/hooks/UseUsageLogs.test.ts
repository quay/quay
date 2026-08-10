import {exportLogs, getAggregateLogs, getLogs} from './UseUsageLogs';
import axios from 'src/libs/axios';

vi.mock('src/libs/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('src/resources/ErrorHandling', () => ({
  assertHttpCode: vi.fn(),
  ResourceError: class ResourceError extends Error {
    constructor(
      message: string,
      public statusCode: number,
      public data: any,
    ) {
      super(message);
    }
  },
}));

describe('UseUsageLogs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('exportLogs', () => {
    it('posts to org export URL with email callback', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce({data: {export_id: '123'}});
      const result = await exportLogs(
        'myorg',
        null,
        '2024-01-01',
        '2024-01-31',
        'user@example.com',
      );
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/exportlogs?starttime=2024-01-01&endtime=2024-01-31',
        {callback_email: 'user@example.com'},
      );
      expect(result).toEqual({export_id: '123'});
    });

    it('posts to repo export URL with URL callback', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce({data: {export_id: '456'}});
      await exportLogs(
        'myorg',
        'myrepo',
        '2024-01-01',
        '2024-01-31',
        'https://webhook.example.com',
      );
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/repository/myorg/myrepo/exportlogs?starttime=2024-01-01&endtime=2024-01-31',
        {callback_url: 'https://webhook.example.com'},
      );
    });

    it('returns error response data on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce({
        response: {status: 400, data: {error: 'bad request'}},
      });
      const result = await exportLogs(
        'myorg',
        null,
        '2024-01-01',
        '2024-01-31',
        'user@example.com',
      );
      expect(result).toEqual({error: 'bad request'});
    });
  });

  describe('getAggregateLogs', () => {
    it('fetches aggregate logs for organization', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce({
        status: 200,
        data: {aggregated: [{count: 5, kind: 'push_repo'}]},
      });
      const result = await getAggregateLogs(
        'myorg',
        null,
        '2024-01-01',
        '2024-01-31',
      );
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/aggregatelogs',
        {params: {starttime: '2024-01-01', endtime: '2024-01-31'}},
      );
      expect(result).toEqual([{count: 5, kind: 'push_repo'}]);
    });

    it('fetches aggregate logs for repository', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce({
        status: 200,
        data: {aggregated: []},
      });
      await getAggregateLogs('myorg', 'myrepo', '2024-01-01', '2024-01-31');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/myorg/myrepo/aggregatelogs',
        expect.any(Object),
      );
    });

    it('fetches aggregate logs from superuser endpoint', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce({
        status: 200,
        data: {aggregated: []},
      });
      await getAggregateLogs('myorg', null, '2024-01-01', '2024-01-31', true);
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/superuser/aggregatelogs',
        expect.any(Object),
      );
    });

    it('returns LogsUnavailable when search is unavailable', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce({
        status: 200,
        data: {search_unavailable: true, message: 'Logs not ready'},
      });
      const result = await getAggregateLogs(
        'myorg',
        null,
        '2024-01-01',
        '2024-01-31',
      );
      expect(result).toEqual({
        unavailable: true,
        message: 'Logs not ready',
      });
    });
  });

  describe('getLogs', () => {
    it('fetches logs for organization', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce({
        data: {logs: [{kind: 'push_repo'}], next_page: 'token123'},
      });
      const result = await getLogs('myorg', null, '2024-01-01', '2024-01-31');
      expect(result.logs).toEqual([{kind: 'push_repo'}]);
      expect(result.nextPage).toBe('token123');
    });

    it('fetches logs for repository', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce({
        data: {logs: [], next_page: null},
      });
      await getLogs('myorg', 'myrepo', '2024-01-01', '2024-01-31');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/myorg/myrepo/logs',
        expect.any(Object),
      );
    });

    it('fetches logs from superuser endpoint', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce({
        data: {logs: []},
      });
      await getLogs('myorg', null, '2024-01-01', '2024-01-31', null, true);
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/superuser/logs',
        expect.any(Object),
      );
    });

    it('passes next_page parameter for pagination', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce({
        data: {logs: []},
      });
      await getLogs('myorg', null, '2024-01-01', '2024-01-31', 'page2token');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/logs',
        {
          params: {
            starttime: '2024-01-01',
            endtime: '2024-01-31',
            next_page: 'page2token',
          },
        },
      );
    });

    it('returns unavailable state when search is unavailable', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce({
        data: {search_unavailable: true, message: 'Not ready'},
      });
      const result = await getLogs('myorg', null, '2024-01-01', '2024-01-31');
      expect(result.unavailable).toBe(true);
      expect(result.logs).toEqual([]);
    });
  });
});
