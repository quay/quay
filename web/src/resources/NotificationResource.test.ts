import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchNotifications,
  createNotification,
  deleteNotification,
  bulkDeleteNotifications,
  testNotification,
  enableNotification,
  bulkEnableNotifications,
  isNotificationDisabled,
  isNotificationEnabled,
  NotificationEventType,
  NotificationMethodType,
  RepoNotification,
} from './NotificationResource';
import {ResourceError} from './ErrorHandling';

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

/** Creates a minimal RepoNotification for testing. */
function createMockNotification(
  overrides: Partial<RepoNotification> = {},
): RepoNotification {
  return {
    config: {},
    event: NotificationEventType.repoPush,
    event_config: {} as any,
    method: NotificationMethodType.slack,
    title: 'test',
    ...overrides,
  };
}

describe('NotificationResource', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('fetchNotifications', () => {
    it('fetches notifications for a repo', async () => {
      const notifications = [{uuid: 'n1', title: 'test'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({notifications}));

      const result = await fetchNotifications('org', 'repo');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/notification/',
      );
      expect(result).toEqual(notifications);
    });
  });

  describe('createNotification', () => {
    it('creates notification with eventConfig from event_config', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      const notification = createMockNotification({
        event_config: {ref_regex: '.*'} as any,
      });
      await createNotification('org', 'repo', notification);
      const sentBody = vi.mocked(axios.post).mock.calls[0][1];
      expect(sentBody.eventConfig).toEqual({ref_regex: '.*'});
    });
  });

  describe('deleteNotification', () => {
    it('deletes a notification', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteNotification('org', 'repo', 'uuid-1');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/notification/uuid-1',
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.delete).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(deleteNotification('org', 'repo', 'uuid-1')).rejects.toThrow(
        ResourceError,
      );
    });
  });

  describe('bulkDeleteNotifications', () => {
    it('deletes multiple notifications', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockResolvedValueOnce(mockResponse(null, 204));

      await expect(
        bulkDeleteNotifications('org', 'repo', ['u1', 'u2']),
      ).resolves.toBeUndefined();
    });
  });

  describe('testNotification', () => {
    it('tests a notification', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await testNotification('org', 'repo', 'uuid-1');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/notification/uuid-1/test',
      );
    });
  });

  describe('enableNotification', () => {
    it('enables a notification', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await enableNotification('org', 'repo', 'uuid-1');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/repository/org/repo/notification/uuid-1',
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(enableNotification('org', 'repo', 'uuid-1')).rejects.toThrow(
        ResourceError,
      );
    });
  });

  describe('bulkEnableNotifications', () => {
    it('enables multiple notifications', async () => {
      vi.mocked(axios.post)
        .mockResolvedValueOnce(mockResponse({}))
        .mockResolvedValueOnce(mockResponse({}));

      await expect(
        bulkEnableNotifications('org', 'repo', ['u1', 'u2']),
      ).resolves.toBeUndefined();
    });
  });

  describe('isNotificationDisabled', () => {
    it('returns true when number_of_failures >= 3', () => {
      expect(
        isNotificationDisabled(createMockNotification({number_of_failures: 3})),
      ).toBe(true);
      expect(
        isNotificationDisabled(createMockNotification({number_of_failures: 5})),
      ).toBe(true);
    });

    it('returns false when number_of_failures < 3', () => {
      expect(
        isNotificationDisabled(createMockNotification({number_of_failures: 2})),
      ).toBe(false);
      expect(
        isNotificationDisabled(createMockNotification({number_of_failures: 0})),
      ).toBe(false);
    });
  });

  describe('isNotificationEnabled', () => {
    it('is inverse of isNotificationDisabled', () => {
      expect(
        isNotificationEnabled(createMockNotification({number_of_failures: 3})),
      ).toBe(false);
      expect(
        isNotificationEnabled(createMockNotification({number_of_failures: 0})),
      ).toBe(true);
    });
  });
});
