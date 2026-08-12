import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useCreateUser} from './UseCreateUser';
import {createSuperuserUser} from 'src/resources/UserResource';

vi.mock('src/resources/UserResource', () => ({
  createSuperuserUser: vi.fn(),
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

describe('useCreateUser', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('calls createSuperuserUser and fires onSuccess with credentials', async () => {
    vi.mocked(createSuperuserUser).mockResolvedValueOnce({
      username: 'newuser',
      password: 'temppass',
    } as any);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(() => useCreateUser({onSuccess, onError}), {
      wrapper,
    });
    act(() => {
      result.current.createUser({
        username: 'newuser',
        password: 'temppass',
        email: 'new@example.com',
      });
    });
    await waitFor(() =>
      expect(onSuccess).toHaveBeenCalledWith('newuser', 'temppass'),
    );
  });

  it('fires onError on failure', async () => {
    const err = new Error('Username taken');
    vi.mocked(createSuperuserUser).mockRejectedValueOnce(err);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(() => useCreateUser({onSuccess, onError}), {
      wrapper,
    });
    act(() => {
      result.current.createUser({
        username: 'taken',
        password: 'pass',
        email: 'x@example.com',
      });
    });
    await waitFor(() => expect(onError).toHaveBeenCalledWith(err));
  });
});
