import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  getOrgMirrorConfig,
  createOrgMirrorConfig,
  deleteOrgMirrorConfig,
  syncOrgMirrorNow,
  verifyOrgMirrorConnection,
  getOrgMirrorRepos,
  orgMirrorStatusLabels,
  orgMirrorStatusColors,
} from './OrgMirrorResource';

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

describe('OrgMirrorResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('getOrgMirrorConfig', () => {
    it('fetches org mirror config', async () => {
      const config = {is_enabled: true, sync_status: 'SUCCESS'};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(config));

      const result = await getOrgMirrorConfig('myorg');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/mirror',
      );
      expect(result).toEqual(config);
    });
  });

  describe('createOrgMirrorConfig', () => {
    it('creates org mirror config', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}, 201));

      await createOrgMirrorConfig('myorg', {
        external_registry_type: 'quay',
        external_registry_url: 'https://quay.io',
        external_namespace: 'upstream',
        robot_username: 'org+bot',
        visibility: 'private',
        sync_interval: 3600,
        sync_start_date: '2024-01-01T00:00:00Z',
      });
      expect(vi.mocked(axios.post).mock.calls[0][0]).toContain(
        'organization/myorg/mirror',
      );
    });
  });

  describe('deleteOrgMirrorConfig', () => {
    it('deletes org mirror config', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteOrgMirrorConfig('myorg');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/mirror',
      );
    });
  });

  describe('syncOrgMirrorNow', () => {
    it('triggers sync', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(null, 204));

      await syncOrgMirrorNow('myorg');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/mirror/sync-now',
      );
    });
  });

  describe('verifyOrgMirrorConnection', () => {
    it('verifies connection', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(
        mockResponse({success: true, message: 'OK'}),
      );

      const result = await verifyOrgMirrorConnection('myorg');
      expect(result.success).toBe(true);
    });
  });

  describe('getOrgMirrorRepos', () => {
    it('fetches repos with default pagination', async () => {
      const repos = {
        repositories: [],
        page: 1,
        limit: 100,
        total: 0,
        has_next: false,
      };
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(repos));

      const result = await getOrgMirrorRepos('myorg');
      expect(vi.mocked(axios.get).mock.calls[0][1]).toEqual({
        params: {page: 1, limit: 100},
      });
      expect(result).toEqual(repos);
    });

    it('includes status filter when provided', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(
        mockResponse({
          repositories: [],
          page: 1,
          limit: 100,
          total: 0,
          has_next: false,
        }),
      );

      await getOrgMirrorRepos('myorg', 1, 50, 'FAIL');
      expect(vi.mocked(axios.get).mock.calls[0][1]).toEqual({
        params: {page: 1, limit: 50, status: 'FAIL'},
      });
    });
  });

  describe('orgMirrorStatusLabels', () => {
    it('maps all status values', () => {
      expect(orgMirrorStatusLabels.SUCCESS).toBe('Success');
      expect(orgMirrorStatusLabels.FAIL).toBe('Failed');
      expect(orgMirrorStatusLabels.NEVER_RUN).toBe('Pending');
    });
  });

  describe('orgMirrorStatusColors', () => {
    it('maps status to colors', () => {
      expect(orgMirrorStatusColors.SUCCESS).toBe('green');
      expect(orgMirrorStatusColors.FAIL).toBe('red');
      expect(orgMirrorStatusColors.SYNCING).toBe('blue');
    });
  });
});
