import {renderHook, act, waitFor} from '@testing-library/react';
import {usePasswordRecovery} from './UsePasswordRecovery';
import axios from 'src/libs/axios';
import {AxiosError} from 'axios';

vi.mock('src/libs/axios', () => ({
  default: {
    post: vi.fn(),
  },
}));

describe('usePasswordRecovery', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('sends recovery request and returns sent result', async () => {
    vi.mocked(axios.post).mockResolvedValueOnce({
      data: {status: 'sent'},
    });
    const {result} = renderHook(() => usePasswordRecovery());
    let returnVal: unknown;
    await act(async () => {
      returnVal = await result.current.requestRecovery('test@example.com');
    });
    expect(returnVal).toEqual({status: 'sent'});
    expect(result.current.result).toEqual({status: 'sent'});
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
    expect(axios.post).toHaveBeenCalledWith('/api/v1/recovery', {
      email: 'test@example.com',
    });
  });

  it('returns org status when email belongs to an org', async () => {
    vi.mocked(axios.post).mockResolvedValueOnce({
      data: {status: 'org', orgname: 'myorg', orgemail: 'admin@myorg.com'},
    });
    const {result} = renderHook(() => usePasswordRecovery());
    await act(async () => {
      await result.current.requestRecovery('user@myorg.com');
    });
    expect(result.current.result?.status).toBe('org');
    expect(result.current.result?.orgname).toBe('myorg');
  });

  it('sets error message on AxiosError with response message', async () => {
    const axiosErr = new AxiosError('Request failed');
    (axiosErr as any).response = {data: {message: 'Email not found'}};
    vi.mocked(axios.post).mockRejectedValueOnce(axiosErr);
    const {result} = renderHook(() => usePasswordRecovery());
    await act(async () => {
      try {
        await result.current.requestRecovery('unknown@example.com');
      } catch {
        // expected
      }
    });
    expect(result.current.error).toBe('Email not found');
    expect(result.current.isLoading).toBe(false);
  });

  it('sets default error message on unknown error', async () => {
    vi.mocked(axios.post).mockRejectedValueOnce(new Error('Network error'));
    const {result} = renderHook(() => usePasswordRecovery());
    await act(async () => {
      try {
        await result.current.requestRecovery('test@example.com');
      } catch {
        // expected
      }
    });
    expect(result.current.error).toBe('Cannot send recovery email');
  });

  it('resetState clears error and result', async () => {
    vi.mocked(axios.post).mockResolvedValueOnce({data: {status: 'sent'}});
    const {result} = renderHook(() => usePasswordRecovery());
    await act(async () => {
      await result.current.requestRecovery('test@example.com');
    });
    act(() => {
      result.current.resetState();
    });
    expect(result.current.result).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.isLoading).toBe(false);
  });
});
