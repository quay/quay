import {renderHook, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useFetchRobotAccounts} from './useRobotAccounts';
import {fetchRobotsForNamespace} from 'src/resources/RobotsResource';

vi.mock('src/resources/RobotsResource', () => ({
  fetchRobotsForNamespace: vi.fn(),
  createNewRobotForNamespace: vi.fn(),
  updateRepoPermsForRobot: vi.fn(),
  bulkDeleteRepoPermsForRobot: vi.fn(),
  bulkUpdateRepoPermsForRobot: vi.fn(),
  fetchRobotPermissionsForNamespace: vi.fn(),
  fetchRobotAccountToken: vi.fn(),
  regenerateRobotToken: vi.fn(),
  addDefaultPermsForRobot: vi.fn(),
  createRobotAccount: vi.fn(),
}));

vi.mock('src/libs/utils', () => ({
  isNullOrUndefined: (v: unknown) => v === null || v === undefined,
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

describe('useFetchRobotAccounts', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('fetches robot accounts for namespace', async () => {
    const mockRobots = [{name: 'myorg+robot1', description: 'Test robot'}];
    vi.mocked(fetchRobotsForNamespace).mockResolvedValueOnce(mockRobots as any);
    const {result} = renderHook(() => useFetchRobotAccounts('myorg'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.robots).toEqual(mockRobots);
    expect(result.current.isLoadingRobots).toBe(false);
    expect(fetchRobotsForNamespace).toHaveBeenCalledWith(
      'myorg',
      false,
      expect.any(Object),
    );
  });

  it('does not fetch when enabled=false', () => {
    renderHook(() => useFetchRobotAccounts('myorg', false, false), {wrapper});
    expect(fetchRobotsForNamespace).not.toHaveBeenCalled();
  });

  it('reports error on fetch failure', async () => {
    vi.mocked(fetchRobotsForNamespace).mockRejectedValueOnce(
      new Error('Forbidden'),
    );
    const {result} = renderHook(() => useFetchRobotAccounts('myorg'), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
