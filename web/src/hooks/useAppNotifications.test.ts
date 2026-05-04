import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useAppNotifications} from './useAppNotifications';
import axios from 'src/libs/axios';

vi.mock('src/libs/axios', () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
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

describe('useAppNotifications', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches notifications and maps levels', async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({
      data: {
        notifications: [
          {
            id: '1',
            kind: 'push',
            message: 'Push event',
            level: 'info',
            read: false,
          },
          {
            id: '2',
            kind: 'vuln',
            message: 'Vuln found',
            level: 'error',
            read: true,
          },
        ],
      },
    });

    const {result} = renderHook(() => useAppNotifications(), {wrapper});
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.notifications).toHaveLength(2);
    expect(result.current.notifications[0].level).toBe('info');
    expect(result.current.notifications[1].level).toBe('danger');
  });

  it('calculates unread count', async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({
      data: {
        notifications: [
          {id: '1', level: 'info', read: false},
          {id: '2', level: 'info', read: false},
          {id: '3', level: 'info', read: true},
        ],
      },
    });

    const {result} = renderHook(() => useAppNotifications(), {wrapper});
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.unreadCount).toBe(2);
  });

  it('maps vulnerability priority to correct level', async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({
      data: {
        notifications: [
          {
            id: '1',
            level: 'info',
            read: false,
            metadata: {vulnerability: {priority: 'Critical'}},
          },
          {
            id: '2',
            level: 'info',
            read: false,
            metadata: {vulnerability: {priority: 'Medium'}},
          },
          {
            id: '3',
            level: 'info',
            read: false,
            metadata: {vulnerability: {priority: 'Low'}},
          },
        ],
      },
    });

    const {result} = renderHook(() => useAppNotifications(), {wrapper});
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.notifications[0].level).toBe('danger');
    expect(result.current.notifications[1].level).toBe('warning');
    expect(result.current.notifications[2].level).toBe('info');
  });

  it('dismisses a notification', async () => {
    vi.mocked(axios.get).mockResolvedValue({
      data: {notifications: [{id: 'n1', level: 'info', read: false}]},
    });
    vi.mocked(axios.put).mockResolvedValue({status: 200});

    const {result} = renderHook(() => useAppNotifications(), {wrapper});
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.dismissNotification('n1');
    });

    await waitFor(() =>
      expect(axios.put).toHaveBeenCalledWith('/api/v1/user/notifications/n1', {
        dismissed: true,
      }),
    );
  });

  it('returns empty array when no notifications', async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({
      data: {notifications: []},
    });

    const {result} = renderHook(() => useAppNotifications(), {wrapper});
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.notifications).toEqual([]);
    expect(result.current.unreadCount).toBe(0);
  });
});
