import {AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  getMirrorConfig,
  createMirrorConfig,
  toggleMirroring,
  syncMirror,
  cancelSync,
  timestampToISO,
  timestampFromISO,
  statusLabels,
} from './MirroringResource';

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

describe('MirroringResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('getMirrorConfig', () => {
    it('fetches mirror configuration', async () => {
      const config = {is_enabled: true, sync_status: 'SYNC_SUCCESS'};
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse(config));

      const result = await getMirrorConfig('org', 'repo');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/mirror',
      );
      expect(result).toEqual(config);
    });
  });

  describe('createMirrorConfig', () => {
    it('creates mirror configuration', async () => {
      const config = {
        is_enabled: true,
        external_reference: 'docker.io/library/nginx',
        robot_username: 'org+bot',
        external_registry_config: {
          verify_tls: true,
          unsigned_images: false,
          proxy: {http_proxy: null, https_proxy: null, no_proxy: null},
        },
        sync_start_date: '2024-01-01T00:00:00Z',
        sync_interval: 86400,
        root_rule: {rule_kind: 'tag_glob_csv', rule_value: ['*']},
      };
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(config, 201));

      const result = await createMirrorConfig('org', 'repo', config);
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/mirror',
        config,
      );
      expect(result).toEqual(config);
    });
  });

  describe('toggleMirroring', () => {
    it('enables mirroring', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}, 201));

      await toggleMirroring('org', 'repo', true);
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/mirror',
        {is_enabled: true},
      );
    });

    it('disables mirroring', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}, 201));

      await toggleMirroring('org', 'repo', false);
      expect(vi.mocked(axios.put).mock.calls[0][1]).toEqual({
        is_enabled: false,
      });
    });
  });

  describe('syncMirror', () => {
    it('triggers sync-now', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(null, 204));

      await syncMirror('org', 'repo');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/mirror/sync-now',
      );
    });
  });

  describe('cancelSync', () => {
    it('cancels a sync', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse(null, 204));

      await cancelSync('org', 'repo');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/mirror/sync-cancel',
      );
    });
  });

  describe('timestampToISO', () => {
    it('converts unix timestamp to ISO string without milliseconds', () => {
      const result = timestampToISO(1704067200);
      expect(result).toBe('2024-01-01T00:00:00Z');
    });
  });

  describe('timestampFromISO', () => {
    it('converts ISO string to unix timestamp', () => {
      const result = timestampFromISO('2024-01-01T00:00:00Z');
      expect(result).toBe(1704067200);
    });

    it('is inverse of timestampToISO', () => {
      const ts = 1704067200;
      expect(timestampFromISO(timestampToISO(ts))).toBe(ts);
    });
  });

  describe('statusLabels', () => {
    it('maps sync statuses to display labels', () => {
      expect(statusLabels.NEVER_RUN).toBe('Scheduled');
      expect(statusLabels.SYNC_FAILED).toBe('Failed');
      expect(statusLabels.SYNC_SUCCESS).toBe('Success');
    });
  });
});
