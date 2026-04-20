import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchAllRobots,
  fetchRobotsForNamespace,
  createNewRobotForNamespace,
  deleteRobotAccount,
  bulkDeleteRobotAccounts,
  RobotDeleteError,
  fetchRobotPermissionsForNamespace,
  fetchRobotAccountToken,
  regenerateRobotToken,
  fetchRobotFederationConfig,
  createRobotFederationConfig,
  IRobot,
} from './RobotsResource';

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

describe('RobotsResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchRobotsForNamespace', () => {
    it('fetches robots for an organization', async () => {
      const controller = new AbortController();
      const robots = [{name: 'org+bot1'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({robots}));

      const result = await fetchRobotsForNamespace(
        'org',
        false,
        controller.signal,
      );
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain(
        'organization/org',
      );
      expect(result).toEqual(robots);
    });

    it('uses user path when isUser=true', async () => {
      const controller = new AbortController();
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({robots: []}));

      await fetchRobotsForNamespace('user1', true, controller.signal);
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain('/user/robots');
    });
  });

  describe('fetchAllRobots', () => {
    it('fetches robots for multiple orgs in parallel', async () => {
      const controller = new AbortController();
      vi.mocked(axios.get)
        .mockResolvedValueOnce(mockResponse({robots: [{name: 'org1+bot'}]}))
        .mockResolvedValueOnce(mockResponse({robots: [{name: 'org2+bot'}]}));

      const result = await fetchAllRobots(['org1', 'org2'], controller.signal);
      expect(result).toHaveLength(2);
    });
  });

  describe('createNewRobotForNamespace', () => {
    it('creates a robot for an organization', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(
        mockResponse({name: 'org+newbot'}, 201),
      );

      const result = await createNewRobotForNamespace('org', 'newbot', 'A bot');
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/organization/org/robots/newbot',
        {description: 'A bot'},
      );
      expect(result).toEqual({name: 'org+newbot'});
    });

    it('uses user path when isUser=true', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}, 201));

      await createNewRobotForNamespace('user1', 'mybot', 'desc', true);
      expect(vi.mocked(axios.put).mock.calls[0][0]).toContain(
        '/user/robots/mybot',
      );
    });
  });

  describe('deleteRobotAccount', () => {
    it('deletes robot account stripping org prefix', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteRobotAccount('org', 'org+bot1');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/organization/org/robots/bot1',
      );
    });

    it('throws RobotDeleteError on failure', async () => {
      vi.mocked(axios.delete).mockRejectedValueOnce(new AxiosError('fail'));

      try {
        await deleteRobotAccount('org', 'org+bot1');
        expect.unreachable('should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(RobotDeleteError);
        expect((err as RobotDeleteError).robotName).toBe('org+bot1');
      }
    });
  });

  describe('bulkDeleteRobotAccounts', () => {
    it('deletes multiple robot accounts', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockResolvedValueOnce(mockResponse(null, 204));

      const robots: IRobot[] = [
        {name: 'org+bot1', created: '', last_accessed: '', description: ''},
        {name: 'org+bot2', created: '', last_accessed: '', description: ''},
      ];
      const result = await bulkDeleteRobotAccounts('org', robots);
      expect(result).toHaveLength(2);
    });
  });

  describe('fetchRobotPermissionsForNamespace', () => {
    it('fetches permissions stripping org prefix from robot name', async () => {
      const controller = new AbortController();
      const permissions = [{repoName: 'repo1', role: 'read'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({permissions}));

      const result = await fetchRobotPermissionsForNamespace(
        'org',
        'org+bot1',
        false,
        controller.signal,
      );
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain(
        '/robots/bot1/permissions',
      );
      expect(result).toEqual(permissions);
    });
  });

  describe('fetchRobotAccountToken', () => {
    it('fetches robot token', async () => {
      const controller = new AbortController();
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({token: 'secret'}),
      );

      const result = await fetchRobotAccountToken(
        'org',
        'org+bot1',
        false,
        controller.signal,
      );
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain('/robots/bot1');
      expect(result).toEqual({token: 'secret'});
    });
  });

  describe('regenerateRobotToken', () => {
    it('regenerates token via POST', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(
        mockResponse({token: 'newtoken'}),
      );

      const result = await regenerateRobotToken('org', 'org+bot1');
      expect(vi.mocked(axios.post).mock.calls[0][0]).toContain(
        '/robots/bot1/regenerate',
      );
      expect(result).toEqual({token: 'newtoken'});
    });
  });

  describe('fetchRobotFederationConfig', () => {
    it('fetches federation config', async () => {
      const controller = new AbortController();
      const config = [{issuer: 'https://example.com', subject: 'sub1'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(config));

      const result = await fetchRobotFederationConfig(
        'org',
        'org+bot1',
        controller.signal,
      );
      expect(vi.mocked(axios.get).mock.calls[0][0]).toContain(
        '/robots/bot1/federation',
      );
      expect(result).toEqual(config);
    });
  });

  describe('createRobotFederationConfig', () => {
    it('creates federation config', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      const config = [{issuer: 'https://example.com', subject: 'sub1'}];
      await createRobotFederationConfig('org', 'org+bot1', config);
      expect(vi.mocked(axios.post).mock.calls[0][0]).toContain(
        '/robots/bot1/federation',
      );
      expect(vi.mocked(axios.post).mock.calls[0][1]).toEqual(config);
    });
  });

  describe('RobotDeleteError', () => {
    it('stores robotName and error', () => {
      const axiosErr = new AxiosError('fail');
      const err = new RobotDeleteError('delete failed', 'org+bot', axiosErr);
      expect(err).toBeInstanceOf(Error);
      expect(err).toBeInstanceOf(RobotDeleteError);
      expect(err.robotName).toBe('org+bot');
      expect(err.error).toBe(axiosErr);
    });
  });
});
