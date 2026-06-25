import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useRobotFederation} from './useRobotFederation';
import {
  fetchRobotFederationConfig,
  createRobotFederationConfig,
} from 'src/resources/RobotsResource';

vi.mock('src/resources/RobotsResource', () => ({
  fetchRobotFederationConfig: vi.fn(),
  createRobotFederationConfig: vi.fn(),
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

describe('useRobotFederation', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('fetches robot federation config', async () => {
    const mockConfig = [
      {issuer: 'https://oidc.example.com', subject: 'robot-subject'},
    ];
    vi.mocked(fetchRobotFederationConfig).mockResolvedValueOnce(
      mockConfig as any,
    );
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(
      () =>
        useRobotFederation({
          namespace: 'myorg',
          robotName: 'myorg+robot1',
          onSuccess,
          onError,
        }),
      {wrapper},
    );
    await waitFor(() =>
      expect(result.current.robotFederationConfig).toBeDefined(),
    );
    expect(result.current.robotFederationConfig).toEqual(mockConfig);
    expect(result.current.loading).toBe(false);
  });

  it('sets robot federation config on mutation success', async () => {
    const mockConfig = [{issuer: 'https://oidc.example.com', subject: 'sub'}];
    vi.mocked(fetchRobotFederationConfig).mockResolvedValueOnce([] as any);
    vi.mocked(createRobotFederationConfig).mockResolvedValueOnce(
      mockConfig as any,
    );
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(
      () =>
        useRobotFederation({
          namespace: 'myorg',
          robotName: 'myorg+robot1',
          onSuccess,
          onError,
        }),
      {wrapper},
    );
    await waitFor(() =>
      expect(result.current.robotFederationConfig).toBeDefined(),
    );
    act(() => {
      result.current.setRobotFederationConfig({
        namespace: 'myorg',
        robotName: 'myorg+robot1',
        config: mockConfig,
      } as any);
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(mockConfig));
  });
});
