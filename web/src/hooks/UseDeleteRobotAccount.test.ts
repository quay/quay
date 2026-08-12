import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useDeleteRobotAccounts} from './UseDeleteRobotAccount';
import {bulkDeleteRobotAccounts} from 'src/resources/RobotsResource';

vi.mock('src/resources/RobotsResource', () => ({
  bulkDeleteRobotAccounts: vi.fn(),
}));

function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

describe('useDeleteRobotAccounts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls bulkDeleteRobotAccounts and fires onSuccess', async () => {
    vi.mocked(bulkDeleteRobotAccounts).mockResolvedValueOnce(undefined);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(
      () => useDeleteRobotAccounts({namespace: 'myorg', onSuccess, onError}),
      {wrapper},
    );
    const robots = [{name: 'myorg+bot1'} as any];
    act(() => {
      result.current.deleteRobotAccounts(robots);
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(bulkDeleteRobotAccounts).toHaveBeenCalledWith('myorg', robots);
  });

  it('fires onError on failure', async () => {
    const err = new Error('delete failed');
    vi.mocked(bulkDeleteRobotAccounts).mockRejectedValueOnce(err);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(
      () => useDeleteRobotAccounts({namespace: 'myorg', onSuccess, onError}),
      {wrapper},
    );
    act(() => {
      result.current.deleteRobotAccounts([{name: 'myorg+bot1'} as any]);
    });
    await waitFor(() => expect(onError).toHaveBeenCalledWith(err));
  });
});
