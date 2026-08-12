import {renderHook, act} from '@testing-library/react';
import {useGlobalFreshLogin} from './UseGlobalFreshLogin';
import {verifyUser} from 'src/resources/AuthResource';
import {
  getCsrfToken,
  retryPendingFreshLoginRequests,
  clearPendingFreshLoginRequests,
} from 'src/libs/axios';

vi.mock('src/resources/AuthResource', () => ({
  verifyUser: vi.fn(),
}));

vi.mock('src/libs/axios', () => ({
  getCsrfToken: vi.fn(),
  retryPendingFreshLoginRequests: vi.fn(),
  clearPendingFreshLoginRequests: vi.fn(),
}));

describe('UseGlobalFreshLogin', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns initial state with isLoading=false', () => {
    const {result} = renderHook(() => useGlobalFreshLogin());
    expect(result.current.isLoading).toBe(false);
    expect(typeof result.current.handleVerify).toBe('function');
    expect(typeof result.current.handleCancel).toBe('function');
  });

  it('verifies user, refreshes CSRF token, and retries queued requests on success', async () => {
    vi.mocked(verifyUser).mockResolvedValueOnce(undefined);
    vi.mocked(getCsrfToken).mockResolvedValueOnce(undefined);

    const {result} = renderHook(() => useGlobalFreshLogin());

    await act(async () => {
      await result.current.handleVerify('correctpassword');
    });

    expect(verifyUser).toHaveBeenCalledWith('correctpassword');
    expect(getCsrfToken).toHaveBeenCalled();
    expect(retryPendingFreshLoginRequests).toHaveBeenCalled();
    expect(result.current.isLoading).toBe(false);
  });

  it('clears pending requests and throws on verification failure', async () => {
    const axiosError = {
      response: {data: {message: 'Invalid password'}},
    };
    vi.mocked(verifyUser).mockRejectedValueOnce(axiosError);

    const {result} = renderHook(() => useGlobalFreshLogin());

    await expect(
      act(async () => {
        await result.current.handleVerify('wrongpassword');
      }),
    ).rejects.toThrow('Invalid password');

    expect(clearPendingFreshLoginRequests).toHaveBeenCalledWith(
      'Invalid password',
    );
    expect(result.current.isLoading).toBe(false);
  });

  it('uses default error message when response has no message', async () => {
    vi.mocked(verifyUser).mockRejectedValueOnce(new Error('unknown'));

    const {result} = renderHook(() => useGlobalFreshLogin());

    await expect(
      act(async () => {
        await result.current.handleVerify('password');
      }),
    ).rejects.toThrow('Invalid verification credentials');

    expect(clearPendingFreshLoginRequests).toHaveBeenCalledWith(
      'Invalid verification credentials',
    );
  });

  it('cancels pending requests on handleCancel', () => {
    const {result} = renderHook(() => useGlobalFreshLogin());

    act(() => {
      result.current.handleCancel();
    });

    expect(clearPendingFreshLoginRequests).toHaveBeenCalledWith(
      'Verification canceled',
    );
    expect(result.current.isLoading).toBe(false);
  });
});
