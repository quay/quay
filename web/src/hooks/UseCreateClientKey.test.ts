import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useCreateClientKey} from './UseCreateClientKey';
import {createClientKey} from 'src/resources/UserResource';

vi.mock('src/resources/UserResource', () => ({
  createClientKey: vi.fn(),
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

describe('useCreateClientKey', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('calls createClientKey with password and fires onSuccess', async () => {
    vi.mocked(createClientKey).mockResolvedValueOnce('clientkey123');
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(
      () => useCreateClientKey({onSuccess, onError}),
      {wrapper},
    );
    act(() => {
      result.current.createClientKey('mypassword');
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(createClientKey).toHaveBeenCalledWith('mypassword');
    expect(result.current.clientKey).toBe('clientkey123');
  });

  it('fires onError on failure', async () => {
    const err = new Error('Wrong password');
    vi.mocked(createClientKey).mockRejectedValueOnce(err);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(
      () => useCreateClientKey({onSuccess, onError}),
      {wrapper},
    );
    act(() => {
      result.current.createClientKey('badpassword');
    });
    await waitFor(() => expect(onError).toHaveBeenCalledWith(err));
  });
});
