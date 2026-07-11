import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useUpdateNamespaceNotifications} from './UseUpdateNamespaceNotifications';
import {
  createNamespaceNotification,
  bulkDeleteNamespaceNotifications,
  testNamespaceNotification,
  bulkEnableNamespaceNotifications,
} from 'src/resources/NamespaceNotificationResource';

vi.mock('src/resources/NamespaceNotificationResource', () => ({
  createNamespaceNotification: vi.fn(),
  bulkDeleteNamespaceNotifications: vi.fn(),
  testNamespaceNotification: vi.fn(),
  bulkEnableNamespaceNotifications: vi.fn(),
}));

function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

describe('useUpdateNamespaceNotifications', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates a notification and fires success', async () => {
    vi.mocked(createNamespaceNotification).mockResolvedValueOnce(undefined);
    const {result} = renderHook(
      () => useUpdateNamespaceNotifications('myorg'),
      {wrapper},
    );
    const notification = {
      event: 'quota_warning',
      method: 'email',
      config: {},
    } as any;
    act(() => {
      result.current.create(notification);
    });
    await waitFor(() =>
      expect(result.current.successCreatingNotification).toBe(true),
    );
    expect(createNamespaceNotification).toHaveBeenCalledWith(
      'myorg',
      notification,
      false,
    );
  });

  it('create error extracts axios detail message', async () => {
    const axiosError = Object.assign(new Error('fail'), {
      isAxiosError: true,
      response: {data: {detail: 'Quota limit exceeded'}},
    });
    vi.mocked(createNamespaceNotification).mockRejectedValueOnce(axiosError);
    const {result} = renderHook(
      () => useUpdateNamespaceNotifications('myorg'),
      {wrapper},
    );
    act(() => {
      result.current.create({} as any);
    });
    await waitFor(() =>
      expect(result.current.errorCreatingNotification).not.toBeNull(),
    );
  });

  it('deletes notifications by uuid', async () => {
    vi.mocked(bulkDeleteNamespaceNotifications).mockResolvedValueOnce(
      undefined,
    );
    const {result} = renderHook(
      () => useUpdateNamespaceNotifications('myorg'),
      {wrapper},
    );
    act(() => {
      result.current.deleteNotifications('uuid-1');
    });
    await waitFor(() =>
      expect(result.current.successDeletingNotification).toBe(true),
    );
    expect(bulkDeleteNamespaceNotifications).toHaveBeenCalledWith(
      'myorg',
      ['uuid-1'],
      false,
    );
  });

  it('enables notifications by uuid', async () => {
    vi.mocked(bulkEnableNamespaceNotifications).mockResolvedValueOnce(
      undefined,
    );
    const {result} = renderHook(
      () => useUpdateNamespaceNotifications('myorg'),
      {wrapper},
    );
    act(() => {
      result.current.enableNotifications(['uuid-1', 'uuid-2']);
    });
    await waitFor(() =>
      expect(result.current.successEnablingNotification).toBe(true),
    );
    expect(bulkEnableNamespaceNotifications).toHaveBeenCalledWith(
      'myorg',
      ['uuid-1', 'uuid-2'],
      false,
    );
  });

  it('tests a notification and fires success', async () => {
    vi.mocked(testNamespaceNotification).mockResolvedValueOnce(undefined);
    const {result} = renderHook(
      () => useUpdateNamespaceNotifications('myorg'),
      {wrapper},
    );
    act(() => {
      result.current.test('uuid-1');
    });
    await waitFor(() =>
      expect(result.current.successTestingNotification).toBe(true),
    );
    expect(testNamespaceNotification).toHaveBeenCalledWith(
      'myorg',
      'uuid-1',
      false,
    );
  });

  it('test mutation reports error on failure', async () => {
    vi.mocked(testNamespaceNotification).mockRejectedValueOnce(
      new Error('Test failed'),
    );
    const {result} = renderHook(
      () => useUpdateNamespaceNotifications('myorg'),
      {wrapper},
    );
    act(() => {
      result.current.test('uuid-1');
    });
    await waitFor(() =>
      expect(result.current.errorTestingNotification).toBe(true),
    );
  });

  it('delete mutation reports error on failure', async () => {
    vi.mocked(bulkDeleteNamespaceNotifications).mockRejectedValueOnce(
      new Error('Delete failed'),
    );
    const {result} = renderHook(
      () => useUpdateNamespaceNotifications('myorg'),
      {wrapper},
    );
    act(() => {
      result.current.deleteNotifications('uuid-1');
    });
    await waitFor(() =>
      expect(result.current.errorDeletingNotification).toBe(true),
    );
  });
});
