import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useNamespaceNotifications,
  NamespaceNotificationStatus,
} from './UseNamespaceNotifications';
import {
  fetchNamespaceNotifications,
  isNamespaceNotificationDisabled,
  isNamespaceNotificationEnabled,
  NamespaceNotificationEventType,
  NamespaceNotification,
} from 'src/resources/NamespaceNotificationResource';

vi.mock('src/resources/NamespaceNotificationResource', () => ({
  fetchNamespaceNotifications: vi.fn(),
  isNamespaceNotificationDisabled: vi.fn(),
  isNamespaceNotificationEnabled: vi.fn(),
  NamespaceNotificationEventType: {
    quotaWarning: 'quota_warning',
    quotaError: 'quota_error',
  },
}));

function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

const mockNotifications = [
  {uuid: 'n1', event: 'quota_warning', config: {}, event_config: {}},
  {uuid: 'n2', event: 'quota_error', config: {}, event_config: {}},
  {uuid: 'n3', event: 'quota_warning', config: {}, event_config: {}},
];

describe('useNamespaceNotifications', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches and returns all notifications', async () => {
    vi.mocked(fetchNamespaceNotifications).mockResolvedValueOnce(
      mockNotifications as NamespaceNotification[],
    );
    const {result} = renderHook(() => useNamespaceNotifications('myorg'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.notifications).toHaveLength(3);
  });

  it('filters notifications by event type', async () => {
    vi.mocked(fetchNamespaceNotifications).mockResolvedValueOnce(
      mockNotifications as NamespaceNotification[],
    );
    const {result} = renderHook(() => useNamespaceNotifications('myorg'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({
        event: [NamespaceNotificationEventType.quotaWarning],
        status: [],
      });
    });
    expect(result.current.notifications).toHaveLength(2);
  });

  it('filters notifications by enabled status', async () => {
    vi.mocked(fetchNamespaceNotifications).mockResolvedValueOnce(
      mockNotifications as NamespaceNotification[],
    );
    vi.mocked(isNamespaceNotificationEnabled).mockImplementation(
      (n: NamespaceNotification) => n.uuid === 'n1',
    );
    const {result} = renderHook(() => useNamespaceNotifications('myorg'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({
        event: [],
        status: [NamespaceNotificationStatus.enabled],
      });
    });
    expect(result.current.notifications).toHaveLength(1);
    expect(result.current.notifications[0].uuid).toBe('n1');
  });

  it('filters by disabled status', async () => {
    vi.mocked(fetchNamespaceNotifications).mockResolvedValueOnce(
      mockNotifications as NamespaceNotification[],
    );
    vi.mocked(isNamespaceNotificationDisabled).mockImplementation(
      (n: NamespaceNotification) => n.uuid !== 'n1',
    );
    const {result} = renderHook(() => useNamespaceNotifications('myorg'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({
        event: [],
        status: [NamespaceNotificationStatus.disabled],
      });
    });
    expect(result.current.notifications).toHaveLength(2);
  });

  it('shows all when both statuses selected', async () => {
    vi.mocked(fetchNamespaceNotifications).mockResolvedValueOnce(
      mockNotifications as NamespaceNotification[],
    );
    const {result} = renderHook(() => useNamespaceNotifications('myorg'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({
        event: [],
        status: [
          NamespaceNotificationStatus.enabled,
          NamespaceNotificationStatus.disabled,
        ],
      });
    });
    expect(result.current.notifications).toHaveLength(3);
  });

  it('resetFilter clears all filters', async () => {
    vi.mocked(fetchNamespaceNotifications).mockResolvedValueOnce(
      mockNotifications as NamespaceNotification[],
    );
    const {result} = renderHook(() => useNamespaceNotifications('myorg'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({
        event: [NamespaceNotificationEventType.quotaWarning],
        status: [],
      });
    });
    expect(result.current.notifications).toHaveLength(2);
    act(() => {
      result.current.resetFilter();
    });
    expect(result.current.notifications).toHaveLength(3);
  });

  it('resetFilter clears a specific field', async () => {
    vi.mocked(fetchNamespaceNotifications).mockResolvedValueOnce(
      mockNotifications as NamespaceNotification[],
    );
    const {result} = renderHook(() => useNamespaceNotifications('myorg'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({
        event: [NamespaceNotificationEventType.quotaWarning],
        status: [],
      });
    });
    act(() => {
      result.current.resetFilter('event');
    });
    expect(result.current.filter.event).toEqual([]);
  });
});
