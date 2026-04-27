import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useUpdateNotifications} from './UseUpdateNotifications';
import {
  createNotification,
  bulkDeleteNotifications,
  testNotification,
  bulkEnableNotifications,
} from 'src/resources/NotificationResource';

vi.mock('src/resources/NotificationResource', () => ({
  createNotification: vi.fn(),
  bulkDeleteNotifications: vi.fn(),
  testNotification: vi.fn(),
  bulkEnableNotifications: vi.fn(),
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

describe('useUpdateNotifications', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('creates a notification and fires success', async () => {
    vi.mocked(createNotification).mockResolvedValueOnce(undefined);
    const {result} = renderHook(
      () => useUpdateNotifications('myorg', 'myrepo'),
      {wrapper},
    );
    const notification = {
      event: 'repo_push',
      method: 'email',
      config: {},
    } as any;
    act(() => {
      result.current.create(notification);
    });
    await waitFor(() =>
      expect(result.current.successCreatingNotification).toBe(true),
    );
    expect(createNotification).toHaveBeenCalledWith(
      'myorg',
      'myrepo',
      notification,
    );
  });

  it('deletes notifications by uuid', async () => {
    vi.mocked(bulkDeleteNotifications).mockResolvedValueOnce(undefined);
    const {result} = renderHook(
      () => useUpdateNotifications('myorg', 'myrepo'),
      {wrapper},
    );
    act(() => {
      result.current.deleteNotifications('uuid-1');
    });
    await waitFor(() =>
      expect(result.current.successDeletingNotification).toBe(true),
    );
    expect(bulkDeleteNotifications).toHaveBeenCalledWith('myorg', 'myrepo', [
      'uuid-1',
    ]);
  });

  it('enables notifications by uuid', async () => {
    vi.mocked(bulkEnableNotifications).mockResolvedValueOnce(undefined);
    const {result} = renderHook(
      () => useUpdateNotifications('myorg', 'myrepo'),
      {wrapper},
    );
    act(() => {
      result.current.enableNotifications(['uuid-1', 'uuid-2']);
    });
    await waitFor(() =>
      expect(result.current.successEnablingNotification).toBe(true),
    );
    expect(bulkEnableNotifications).toHaveBeenCalledWith('myorg', 'myrepo', [
      'uuid-1',
      'uuid-2',
    ]);
  });

  it('tests a notification and fires success', async () => {
    vi.mocked(testNotification).mockResolvedValueOnce(undefined);
    const {result} = renderHook(
      () => useUpdateNotifications('myorg', 'myrepo'),
      {wrapper},
    );
    act(() => {
      result.current.test('uuid-1');
    });
    await waitFor(() =>
      expect(result.current.successTestingNotification).toBe(true),
    );
    expect(testNotification).toHaveBeenCalledWith('myorg', 'myrepo', 'uuid-1');
  });

  it('test mutation reports error on failure', async () => {
    vi.mocked(testNotification).mockRejectedValueOnce(
      new Error('Test failed'),
    );
    const {result} = renderHook(
      () => useUpdateNotifications('myorg', 'myrepo'),
      {wrapper},
    );
    act(() => {
      result.current.test('uuid-1');
    });
    await waitFor(() =>
      expect(result.current.errorTestingNotification).toBe(true),
    );
  });
});
