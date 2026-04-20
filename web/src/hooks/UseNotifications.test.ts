import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useNotifications, NotifiationStatus} from './UseNotifications';
import {
  fetchNotifications,
  isNotificationDisabled,
  isNotificationEnabled,
  NotificationEventType,
} from 'src/resources/NotificationResource';

vi.mock('src/resources/NotificationResource', () => ({
  fetchNotifications: vi.fn(),
  isNotificationDisabled: vi.fn(),
  isNotificationEnabled: vi.fn(),
  NotificationEventType: {
    repo_push: 'repo_push',
    build_failure: 'build_failure',
  },
}));

/** QueryClientProvider wrapper for hooks that use React Query. */
function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

const mockNotifications = [
  {uuid: 'n1', event: 'repo_push', config: {}, event_config: {}},
  {uuid: 'n2', event: 'build_failure', config: {}, event_config: {}},
  {uuid: 'n3', event: 'repo_push', config: {}, event_config: {}},
];

describe('useNotifications', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('fetches and returns all notifications', async () => {
    vi.mocked(fetchNotifications).mockResolvedValueOnce(
      mockNotifications as any,
    );
    const {result} = renderHook(() => useNotifications('myorg', 'myrepo'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.notifications).toHaveLength(3);
    expect(result.current.paginatedNotifications).toHaveLength(3);
  });

  it('filters notifications by event type', async () => {
    vi.mocked(fetchNotifications).mockResolvedValueOnce(
      mockNotifications as any,
    );
    const {result} = renderHook(() => useNotifications('myorg', 'myrepo'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({
        event: [NotificationEventType.repo_push as any],
        status: [],
      });
    });
    expect(result.current.paginatedNotifications).toHaveLength(2);
  });

  it('filters notifications by enabled status', async () => {
    vi.mocked(fetchNotifications).mockResolvedValueOnce(
      mockNotifications as any,
    );
    vi.mocked(isNotificationEnabled).mockImplementation(
      (n: any) => n.uuid === 'n1',
    );
    const {result} = renderHook(() => useNotifications('myorg', 'myrepo'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({
        event: [],
        status: [NotifiationStatus.enabled],
      });
    });
    expect(result.current.paginatedNotifications).toHaveLength(1);
    expect(result.current.paginatedNotifications[0].uuid).toBe('n1');
  });

  it('filters by disabled status', async () => {
    vi.mocked(fetchNotifications).mockResolvedValueOnce(
      mockNotifications as any,
    );
    vi.mocked(isNotificationDisabled).mockImplementation(
      (n: any) => n.uuid !== 'n1',
    );
    const {result} = renderHook(() => useNotifications('myorg', 'myrepo'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({
        event: [],
        status: [NotifiationStatus.disabled],
      });
    });
    expect(result.current.paginatedNotifications).toHaveLength(2);
  });

  it('resetFilter clears all filters', async () => {
    vi.mocked(fetchNotifications).mockResolvedValueOnce(
      mockNotifications as any,
    );
    const {result} = renderHook(() => useNotifications('myorg', 'myrepo'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({
        event: ['repo_push' as any],
        status: [],
      });
    });
    expect(result.current.paginatedNotifications).toHaveLength(2);
    act(() => {
      result.current.resetFilter();
    });
    expect(result.current.paginatedNotifications).toHaveLength(3);
  });

  it('resetFilter clears a specific field', async () => {
    vi.mocked(fetchNotifications).mockResolvedValueOnce(
      mockNotifications as any,
    );
    const {result} = renderHook(() => useNotifications('myorg', 'myrepo'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({event: ['repo_push' as any], status: []});
    });
    act(() => {
      result.current.resetFilter('event');
    });
    expect(result.current.filter.event).toEqual([]);
  });
});
