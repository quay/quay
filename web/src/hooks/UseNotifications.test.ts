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
    repoPush: 'repo_push',
    buildFailure: 'build_failure',
    vulnFound: 'vulnerability_found',
    buildQueued: 'build_queued',
    buildStart: 'build_start',
    buildSuccess: 'build_success',
    buildCancelled: 'build_cancelled',
    mirrorStarted: 'repo_mirror_sync_started',
    mirrorSuccess: 'repo_mirror_sync_success',
    mirrorFailed: 'repo_mirror_sync_failed',
    imageExpiry: 'repo_image_expiry',
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
    expect(result.current.filteredNotifications).toHaveLength(3);
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
        event: [NotificationEventType.repoPush],
        status: [],
      });
    });
    expect(result.current.notifications).toHaveLength(3);
    expect(result.current.filteredNotifications).toHaveLength(2);
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
    expect(result.current.filteredNotifications).toHaveLength(1);
    expect(result.current.filteredNotifications[0].uuid).toBe('n1');
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
    expect(result.current.filteredNotifications).toHaveLength(2);
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
    expect(result.current.filteredNotifications).toHaveLength(2);
    act(() => {
      result.current.resetFilter();
    });
    expect(result.current.filteredNotifications).toHaveLength(3);
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

  it('combines event and status filters', async () => {
    vi.mocked(fetchNotifications).mockResolvedValueOnce(
      mockNotifications as any,
    );
    vi.mocked(isNotificationEnabled).mockImplementation(
      (notification: any) => notification.uuid !== 'n3',
    );
    const {result} = renderHook(() => useNotifications('myorg', 'myrepo'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({
        event: [NotificationEventType.repoPush],
        status: [NotifiationStatus.enabled],
      });
    });
    expect(result.current.filteredNotifications.map((n) => n.uuid)).toEqual([
      'n1',
    ]);
  });

  it('returns every matching notification without paginating', async () => {
    const notifications = Array.from({length: 25}, (_, index) => ({
      uuid: `n${index}`,
      event: 'repo_push',
      config: {},
      event_config: {},
    }));
    vi.mocked(fetchNotifications).mockResolvedValueOnce(notifications as any);
    const {result} = renderHook(() => useNotifications('myorg', 'myrepo'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({
        event: [NotificationEventType.repoPush],
        status: [],
      });
    });
    expect(result.current.filteredNotifications).toHaveLength(25);
  });

  it('keeps the active filtered collection stable across rerenders', async () => {
    vi.mocked(fetchNotifications).mockResolvedValueOnce(
      mockNotifications as any,
    );
    const {result, rerender} = renderHook(
      () => useNotifications('myorg', 'myrepo'),
      {wrapper},
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => {
      result.current.setFilter({
        event: [NotificationEventType.repoPush],
        status: [],
      });
    });
    const filteredNotifications = result.current.filteredNotifications;

    rerender();

    expect(result.current.filteredNotifications).toBe(filteredNotifications);
  });

  it('returns a stable empty filtered collection while loading', () => {
    vi.mocked(fetchNotifications).mockImplementation(
      () => new Promise(() => undefined),
    );
    const {result, rerender} = renderHook(
      () => useNotifications('myorg', 'myrepo'),
      {wrapper},
    );
    const filteredNotifications = result.current.filteredNotifications;

    expect(filteredNotifications).toEqual([]);
    rerender();
    expect(result.current.filteredNotifications).toBe(filteredNotifications);
  });
});
