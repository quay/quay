import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useConvertAccount} from './UseConvertAccount';
import {convert} from 'src/resources/UserResource';

vi.mock('src/resources/UserResource', () => ({
  convert: vi.fn(),
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

describe('useConvertAccount', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('calls convert and fires onSuccess', async () => {
    vi.mocked(convert).mockResolvedValueOnce(undefined);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(() => useConvertAccount({onSuccess, onError}), {
      wrapper,
    });
    act(() => {
      result.current.convert({adminUser: 'admin', adminPassword: 'pass'});
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(convert).toHaveBeenCalledWith({
      adminUser: 'admin',
      adminPassword: 'pass',
    });
    expect(result.current.loading).toBe(false);
  });

  it('fires onError on failure', async () => {
    const err = new Error('Conversion failed');
    vi.mocked(convert).mockRejectedValueOnce(err);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(() => useConvertAccount({onSuccess, onError}), {
      wrapper,
    });
    act(() => {
      result.current.convert({adminUser: 'admin', adminPassword: 'wrong'});
    });
    await waitFor(() => expect(onError).toHaveBeenCalledWith(err));
    expect(onSuccess).not.toHaveBeenCalled();
  });

  it('clientKey is undefined since convert() returns void', async () => {
    vi.mocked(convert).mockResolvedValueOnce(undefined);
    const onSuccess = vi.fn();
    const onError = vi.fn();
    const {result} = renderHook(() => useConvertAccount({onSuccess, onError}), {
      wrapper,
    });
    act(() => {
      result.current.convert({adminUser: 'admin', adminPassword: 'pass'});
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
    expect(result.current.clientKey).toBeUndefined();
  });
});
