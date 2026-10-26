import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import axios from 'src/libs/axios';
import {
  fetchNamespaceNotifications,
  createNamespaceNotification,
  deleteNamespaceNotification,
  bulkDeleteNamespaceNotifications,
  testNamespaceNotification,
  enableNamespaceNotification,
  bulkEnableNamespaceNotifications,
  isNamespaceNotificationDisabled,
  isNamespaceNotificationEnabled,
  NamespaceNotificationEventType,
  NamespaceNotificationMethodType,
  NamespaceNotification,
} from './NamespaceNotificationResource';
import {ResourceError} from './ErrorHandling';

vi.mock('src/libs/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

function mockResponse(data: unknown, status = 200): AxiosResponse {
  return {
    data,
    status,
    statusText: 'OK',
    headers: {},
    config: {} as InternalAxiosRequestConfig,
  };
}

function createMockNotification(
  overrides: Partial<NamespaceNotification> = {},
): NamespaceNotification {
  return {
    config: {},
    event: NamespaceNotificationEventType.quotaWarning,
    event_config: {},
    method: NamespaceNotificationMethodType.email,
    title: 'test',
    ...overrides,
  };
}

describe('NamespaceNotificationResource', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchNamespaceNotifications', () => {
    it('fetches notifications for an organization', async () => {
      const notifications = [{uuid: 'n1', title: 'test'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({notifications}));

      const result = await fetchNamespaceNotifications('myorg');
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/notifications',
      );
      expect(result).toEqual(notifications);
    });

    it('fetches notifications for a user', async () => {
      const notifications = [{uuid: 'n1'}];
      vi.mocked(axios.get).mockResolvedValueOnce(mockResponse({notifications}));

      const result = await fetchNamespaceNotifications('user1', true);
      expect(axios.get).toHaveBeenCalledWith(
        '/api/v1/user/namespacenotifications',
      );
      expect(result).toEqual(notifications);
    });
  });

  describe('createNamespaceNotification', () => {
    it('creates notification for an organization', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      const notification = createMockNotification({
        event_config: {threshold: 80},
      });
      await createNamespaceNotification('myorg', notification);
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/notifications',
        expect.objectContaining({
          event: 'quota_warning',
          method: 'email',
          eventConfig: {threshold: 80},
        }),
      );
    });

    it('creates notification for a user', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      const notification = createMockNotification();
      await createNamespaceNotification('user1', notification, true);
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/user/namespacenotifications',
        expect.any(Object),
      );
    });
  });

  describe('deleteNamespaceNotification', () => {
    it('deletes a notification for an organization', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteNamespaceNotification('myorg', 'uuid-1');
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/notifications/uuid-1',
      );
    });

    it('deletes a notification for a user', async () => {
      vi.mocked(axios.delete).mockResolvedValueOnce(mockResponse(null, 204));

      await deleteNamespaceNotification('user1', 'uuid-1', true);
      expect(axios.delete).toHaveBeenCalledWith(
        '/api/v1/user/namespacenotifications/uuid-1',
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.delete).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        deleteNamespaceNotification('myorg', 'uuid-1'),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('bulkDeleteNamespaceNotifications', () => {
    it('deletes multiple notifications', async () => {
      vi.mocked(axios.delete)
        .mockResolvedValueOnce(mockResponse(null, 204))
        .mockResolvedValueOnce(mockResponse(null, 204));

      await expect(
        bulkDeleteNamespaceNotifications('myorg', ['u1', 'u2']),
      ).resolves.toBeUndefined();
      expect(axios.delete).toHaveBeenCalledTimes(2);
    });
  });

  describe('testNamespaceNotification', () => {
    it('tests a notification for an organization', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await testNamespaceNotification('myorg', 'uuid-1');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/notifications/uuid-1/test',
      );
    });

    it('tests a notification for a user', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await testNamespaceNotification('user1', 'uuid-1', true);
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/user/namespacenotifications/uuid-1/test',
      );
    });
  });

  describe('enableNamespaceNotification', () => {
    it('enables a notification for an organization', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await enableNamespaceNotification('myorg', 'uuid-1');
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/organization/myorg/notifications/uuid-1',
      );
    });

    it('enables a notification for a user', async () => {
      vi.mocked(axios.post).mockResolvedValueOnce(mockResponse({}));

      await enableNamespaceNotification('user1', 'uuid-1', true);
      expect(axios.post).toHaveBeenCalledWith(
        '/api/v1/user/namespacenotifications/uuid-1',
      );
    });

    it('throws ResourceError on failure', async () => {
      vi.mocked(axios.post).mockRejectedValueOnce(new AxiosError('fail'));

      await expect(
        enableNamespaceNotification('myorg', 'uuid-1'),
      ).rejects.toThrow(ResourceError);
    });
  });

  describe('bulkEnableNamespaceNotifications', () => {
    it('enables multiple notifications', async () => {
      vi.mocked(axios.post)
        .mockResolvedValueOnce(mockResponse({}))
        .mockResolvedValueOnce(mockResponse({}));

      await expect(
        bulkEnableNamespaceNotifications('myorg', ['u1', 'u2']),
      ).resolves.toBeUndefined();
      expect(axios.post).toHaveBeenCalledTimes(2);
    });
  });

  describe('isNamespaceNotificationDisabled', () => {
    it('returns true when number_of_failures >= 3', () => {
      expect(
        isNamespaceNotificationDisabled(
          createMockNotification({number_of_failures: 3}),
        ),
      ).toBe(true);
      expect(
        isNamespaceNotificationDisabled(
          createMockNotification({number_of_failures: 5}),
        ),
      ).toBe(true);
    });

    it('returns false when number_of_failures < 3', () => {
      expect(
        isNamespaceNotificationDisabled(
          createMockNotification({number_of_failures: 2}),
        ),
      ).toBe(false);
      expect(
        isNamespaceNotificationDisabled(
          createMockNotification({number_of_failures: 0}),
        ),
      ).toBe(false);
    });
  });

  describe('isNamespaceNotificationEnabled', () => {
    it('is inverse of isNamespaceNotificationDisabled', () => {
      expect(
        isNamespaceNotificationEnabled(
          createMockNotification({number_of_failures: 3}),
        ),
      ).toBe(false);
      expect(
        isNamespaceNotificationEnabled(
          createMockNotification({number_of_failures: 0}),
        ),
      ).toBe(true);
    });
  });
});
