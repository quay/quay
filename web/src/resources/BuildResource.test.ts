import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchBuilds,
  fetchBuild,
  fetchBuildTriggers,
  toggleBuildTrigger,
  deleteBuildTrigger,
  startBuild,
  startDockerfileBuild,
  cancelBuild,
  fetchBuildLogs,
  fileDrop,
  fetchBuildLogsSuperuser,
} from './BuildResource';

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

describe('BuildResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchBuilds', () => {
    it('fetches builds with default limit', async () => {
      const builds = [{id: 'b1', phase: 'complete'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({builds}));

      const result = await fetchBuilds('org', 'repo');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/build/',
        {params: {limit: 10}},
      );
      expect(result).toEqual(builds);
    });

    it('includes since param when buildsSinceInSeconds is provided', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({builds: []}));

      await fetchBuilds('org', 'repo', 3600);
      expect(vi.mocked(axios.get).mock.calls[0][1]).toEqual({
        params: {limit: 10, since: 3600},
      });
    });
  });

  describe('fetchBuild', () => {
    it('fetches a single build', async () => {
      const build = {id: 'b1', phase: 'building'};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(build));

      const result = await fetchBuild('org', 'repo', 'b1');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/build/b1',
      );
      expect(result).toEqual(build);
    });
  });

  describe('fetchBuildTriggers', () => {
    it('fetches triggers with abort signal', async () => {
      const controller = new AbortController();
      const triggers = [{id: 't1', service: 'github'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({triggers}));

      const result = await fetchBuildTriggers('org', 'repo', controller.signal);
      expect(result).toEqual(triggers);
    });
  });

  describe('startBuild', () => {
    it('sends commit_sha when ref is a string', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({id: 'b1'}));

      await startBuild('org', 'repo', 'trigger1', 'abc123');
      expect(vi.mocked(axios.post).mock.calls[0][1]).toEqual({
        commit_sha: 'abc123',
      });
    });

    it('sends refs when ref is an object', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({id: 'b1'}));

      const ref = {kind: 'branch', name: 'main'};
      await startBuild('org', 'repo', 'trigger1', ref);
      expect(vi.mocked(axios.post).mock.calls[0][1]).toEqual({refs: ref});
    });
  });

  describe('startDockerfileBuild', () => {
    it('starts a build with file_id', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({id: 'b1'}));

      await startDockerfileBuild('org', 'repo', 'file-123');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/build/',
        {file_id: 'file-123'},
      );
    });

    it('includes pull_robot when provided', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({id: 'b1'}));

      await startDockerfileBuild('org', 'repo', 'file-123', 'org+bot');
      expect(vi.mocked(axios.post).mock.calls[0][1]).toEqual({
        file_id: 'file-123',
        pull_robot: 'org+bot',
      });
    });
  });

  describe('cancelBuild', () => {
    it('cancels a build', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await cancelBuild('org', 'repo', 'b1');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/build/b1',
      );
    });
  });

  describe('fetchBuildLogs', () => {
    it('returns logs directly when no logs_url', async () => {
      const logs = {logs: [{message: 'building'}], start: 0, total: 1};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(logs));

      const result = await fetchBuildLogs('org', 'repo', 'b1');
      expect(result).toEqual(logs);
    });

    it('fetches archived logs when logs_url is present', async () => {
      const archivedLogs = {logs: [{message: 'archived'}], start: 0, total: 1};
      vi.mocked(axios.get)
        .mockResolvedValueOnce(
          mockResponse({logs_url: 'https://archive.example.com/logs'}),
        )
        .mockResolvedValueOnce(mockResponse(archivedLogs));

      const result = await fetchBuildLogs('org', 'repo', 'b1');
      expect(vi.mocked(axios.get).mock.calls[1][0]).toBe(
        'https://archive.example.com/logs',
      );
      expect(result).toEqual(archivedLogs);
    });
  });

  describe('fileDrop', () => {
    it('creates a filedrop', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(
        mockResponse({file_id: 'f1', url: 'https://upload.example.com'}),
      );

      const result = await fileDrop();
      expect(axios.post).toHaveBeenCalledWith('/api/v1/filedrop/', {
        mimeType: 'application/octet-stream',
      });
      expect(result.file_id).toBe('f1');
    });
  });

  describe('fetchBuildLogsSuperuser', () => {
    it('fetches build info and logs in parallel and merges them', async () => {
      const buildData = {id: 'b1', uuid: 'uuid1', status: 'complete'};
      const logsData = {logs: [{message: 'step 1'}, {message: 'step 2'}]};

      vi.mocked(axios.get)
        .mockResolvedValueOnce(mockResponse(buildData))
        .mockResolvedValueOnce(mockResponse(logsData));

      const result = await fetchBuildLogsSuperuser('uuid1');
      expect(result.id).toBe('b1');
      expect(result.logs).toEqual(logsData.logs);
    });

    it('returns empty logs array when logs data has no logs', async () => {
      vi.mocked(axios.get)
        .mockResolvedValueOnce(mockResponse({id: 'b1'}))
        .mockResolvedValueOnce(mockResponse({}));

      const result = await fetchBuildLogsSuperuser('uuid1');
      expect(result.logs).toEqual([]);
    });
  });

  describe('toggleBuildTrigger', () => {
    it('toggles trigger enabled state', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({triggers: []}));

      await toggleBuildTrigger('org', 'repo', 't1', true);
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/trigger/t1',
        {enabled: true},
      );
    });
  });

  describe('deleteBuildTrigger', () => {
    it('deletes a build trigger', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(
        mockResponse({triggers: []}),
      );

      await deleteBuildTrigger('org', 'repo', 't1');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/trigger/t1',
      );
    });
  });
});
