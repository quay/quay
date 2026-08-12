import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchOrganizationQuota,
  createOrganizationQuota,
  updateOrganizationQuota,
  deleteOrganizationQuota,
  createQuotaLimit,
  updateQuotaLimit,
  deleteQuotaLimit,
  bytesToHumanReadable,
  humanReadableToBytes,
} from './QuotaResource';

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

describe('QuotaResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchOrganizationQuota', () => {
    it('uses organization endpoint by default', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse([]));

      await fetchOrganizationQuota('myorg');
      expect(vi.mocked(axios.get).mock.calls[0][0]).toBe(
        '/api/v1/organization/myorg/quota',
      );
    });

    it('uses self endpoint for viewMode=self', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse([]));

      await fetchOrganizationQuota('myuser', undefined, 'self');
      expect(vi.mocked(axios.get).mock.calls[0][0]).toBe('/api/v1/user/quota');
    });

    it('uses superuser endpoint for viewMode=superuser', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse([]));

      await fetchOrganizationQuota('someuser', undefined, 'superuser');
      expect(vi.mocked(axios.get).mock.calls[0][0]).toBe(
        '/api/v1/superuser/users/someuser/quota',
      );
    });

    it('returns empty array on 404', async () => {
      const err = new AxiosError('Not Found');
      (err as any).response = {status: 404};
      vi.mocked(axios.get).mockRejectedValueOnce(err);

      const result = await fetchOrganizationQuota('myorg');
      expect(result).toEqual([]);
    });

    it('returns empty array on 403', async () => {
      const err = new AxiosError('Forbidden');
      (err as any).response = {status: 403};
      vi.mocked(axios.get).mockRejectedValueOnce(err);

      const result = await fetchOrganizationQuota('myorg');
      expect(result).toEqual([]);
    });

    it('returns empty array on CanceledError', async () => {
      const err = new Error('canceled');
      err.name = 'CanceledError';
      vi.mocked(axios.get).mockRejectedValueOnce(err);

      const result = await fetchOrganizationQuota('myorg');
      expect(result).toEqual([]);
    });

    it('re-throws other errors', async () => {
      vi.mocked(axios.get).mockRejectedValueOnce(new Error('network fail'));

      await expect(fetchOrganizationQuota('myorg')).rejects.toThrow(
        'network fail',
      );
    });
  });

  describe('createOrganizationQuota', () => {
    it('uses organization endpoint by default', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await createOrganizationQuota('myorg', {limit_bytes: 1000});
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/quota',
        {limit_bytes: 1000},
      );
    });

    it('uses superuser endpoint for viewMode=superuser', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await createOrganizationQuota('user1', {limit_bytes: 1000}, 'superuser');
      expect(vi.mocked(axios.post).mock.calls[0][0]).toContain('superuser');
    });
  });

  describe('updateOrganizationQuota', () => {
    it('updates quota with correct endpoint', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await updateOrganizationQuota('myorg', 'q1', {limit_bytes: 2000});
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/quota/q1',
        {limit_bytes: 2000},
      );
    });
  });

  describe('deleteOrganizationQuota', () => {
    it('deletes quota with correct endpoint', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteOrganizationQuota('myorg', 'q1');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/quota/q1',
      );
    });
  });

  describe('createQuotaLimit', () => {
    it('creates a quota limit', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await createQuotaLimit('myorg', 'q1', {
        type: 'Warning',
        threshold_percent: 80,
      });
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/quota/q1/limit',
        {type: 'Warning', threshold_percent: 80},
      );
    });
  });

  describe('updateQuotaLimit', () => {
    it('updates a quota limit', async () => {
      vi.mocked(axios.put).mockResolvedValueOnce(mockResponse({}));

      await updateQuotaLimit('myorg', 'q1', 'l1', {
        type: 'Reject',
        threshold_percent: 90,
      });
      expect(axios.put).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/quota/q1/limit/l1',
        {type: 'Reject', threshold_percent: 90},
      );
    });
  });

  describe('deleteQuotaLimit', () => {
    it('deletes a quota limit', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteQuotaLimit('myorg', 'q1', 'l1');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/quota/q1/limit/l1',
      );
    });
  });

  describe('bytesToHumanReadable', () => {
    it('returns bytes for small values', () => {
      expect(bytesToHumanReadable(500)).toEqual({value: 500, unit: 'B'});
    });

    it('converts to KiB', () => {
      expect(bytesToHumanReadable(1024)).toEqual({value: 1, unit: 'KiB'});
    });

    it('converts to MiB', () => {
      expect(bytesToHumanReadable(1024 * 1024)).toEqual({
        value: 1,
        unit: 'MiB',
      });
    });

    it('converts to GiB', () => {
      expect(bytesToHumanReadable(1024 ** 3)).toEqual({value: 1, unit: 'GiB'});
    });

    it('converts to TiB', () => {
      expect(bytesToHumanReadable(1024 ** 4)).toEqual({value: 1, unit: 'TiB'});
    });

    it('rounds to 2 decimal places', () => {
      const result = bytesToHumanReadable(1536);
      expect(result).toEqual({value: 1.5, unit: 'KiB'});
    });
  });

  describe('humanReadableToBytes', () => {
    it('converts KiB to bytes', () => {
      expect(humanReadableToBytes(1, 'KiB')).toBe(1024);
    });

    it('converts GiB to bytes', () => {
      expect(humanReadableToBytes(2, 'GiB')).toBe(2 * 1024 ** 3);
    });

    it('returns value for unknown unit (multiplier=1)', () => {
      expect(humanReadableToBytes(100, 'unknown')).toBe(100);
    });
  });
});
