import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useUsernameValidation} from './UseUsernameValidation';
import axios from 'src/libs/axios';

vi.mock('src/libs/axios', () => ({
  default: {
    get: vi.fn(),
  },
}));

/** QueryClientProvider wrapper for hooks that use React Query mutations. */
function wrapper({children}: {children: React.ReactNode}) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('useUsernameValidation', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('initial state', () => {
    it('initializes with state "editing" and isValidating false', () => {
      const {result} = renderHook(() => useUsernameValidation(), {wrapper});
      expect(result.current.state).toBe('editing');
      expect(result.current.isValidating).toBe(false);
    });
  });

  describe('empty username', () => {
    it('remains in "editing" when empty string is validated', () => {
      const {result} = renderHook(() => useUsernameValidation(), {wrapper});
      act(() => {
        result.current.validateUsername('');
      });
      expect(result.current.state).toBe('editing');
    });
  });

  describe('current username match', () => {
    it('transitions to "confirmed" without API calls when username matches currentUsername', async () => {
      const {result} = renderHook(() => useUsernameValidation('existingUser'), {
        wrapper,
      });
      act(() => {
        result.current.validateUsername('existingUser');
      });
      await waitFor(() => {
        expect(result.current.state).toBe('confirmed');
      });
      expect(axios.get).not.toHaveBeenCalled();
    });
  });

  describe('user exists', () => {
    it('transitions to "existing" when user API returns 200', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce({data: {username: 'taken'}});
      const {result} = renderHook(() => useUsernameValidation(), {wrapper});
      act(() => {
        result.current.validateUsername('taken');
      });
      await waitFor(() => {
        expect(result.current.state).toBe('existing');
      });
    });

    it('calls the user API endpoint with correct username', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce({data: {}});
      const {result} = renderHook(() => useUsernameValidation(), {wrapper});
      act(() => {
        result.current.validateUsername('testUser');
      });
      await waitFor(() => {
        expect(axios.get).toHaveBeenCalledWith('/api/v1/users/testUser');
      });
    });
  });

  describe('user not found, org exists', () => {
    it('transitions to "existing" when user 404s but org returns 200', async () => {
      vi.mocked(axios.get)
        .mockRejectedValueOnce(new Error('Not found'))
        .mockResolvedValueOnce({data: {}});
      const {result} = renderHook(() => useUsernameValidation(), {wrapper});
      act(() => {
        result.current.validateUsername('orgName');
      });
      await waitFor(() => {
        expect(result.current.state).toBe('existing');
      });
    });

    it('calls both user and org API endpoints', async () => {
      vi.mocked(axios.get)
        .mockRejectedValueOnce(new Error('Not found'))
        .mockResolvedValueOnce({data: {}});
      const {result} = renderHook(() => useUsernameValidation(), {wrapper});
      act(() => {
        result.current.validateUsername('testOrg');
      });
      await waitFor(() => {
        expect(axios.get).toHaveBeenCalledTimes(2);
      });
      expect(axios.get).toHaveBeenNthCalledWith(1, '/api/v1/users/testOrg');
      expect(axios.get).toHaveBeenNthCalledWith(
        2,
        '/api/v1/organization/testOrg',
      );
    });
  });

  describe('neither user nor org exists', () => {
    it('transitions to "confirmed" when both APIs 404', async () => {
      vi.mocked(axios.get)
        .mockRejectedValueOnce(new Error('Not found'))
        .mockRejectedValueOnce(new Error('Not found'));
      const {result} = renderHook(() => useUsernameValidation(), {wrapper});
      act(() => {
        result.current.validateUsername('newUser');
      });
      await waitFor(() => {
        expect(result.current.state).toBe('confirmed');
      });
    });
  });

  describe('confirming state', () => {
    it('transitions through "confirming" during validation', async () => {
      let resolveGet: (value: unknown) => void;
      vi.mocked(axios.get).mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveGet = resolve;
          }),
      );
      const {result} = renderHook(() => useUsernameValidation(), {wrapper});
      act(() => {
        result.current.validateUsername('someUser');
      });
      await waitFor(() => {
        expect(result.current.state).toBe('confirming');
      });
      await act(async () => {
        resolveGet!({data: {}});
      });
      await waitFor(() => {
        expect(result.current.state).toBe('existing');
      });
    });
  });

  describe('isValidating', () => {
    it('is true while mutation is in progress', async () => {
      let resolveGet: (value: unknown) => void;
      vi.mocked(axios.get).mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveGet = resolve;
          }),
      );
      const {result} = renderHook(() => useUsernameValidation(), {wrapper});
      act(() => {
        result.current.validateUsername('someUser');
      });
      await waitFor(() => {
        expect(result.current.isValidating).toBe(true);
      });
      await act(async () => {
        resolveGet!({data: {}});
      });
      await waitFor(() => {
        expect(result.current.isValidating).toBe(false);
      });
    });
  });

  describe('no currentUsername provided', () => {
    it('makes API calls when currentUsername is undefined', async () => {
      vi.mocked(axios.get).mockResolvedValueOnce({data: {}});
      const {result} = renderHook(() => useUsernameValidation(), {wrapper});
      act(() => {
        result.current.validateUsername('anyUser');
      });
      await waitFor(() => {
        expect(result.current.state).toBe('existing');
      });
      expect(axios.get).toHaveBeenCalled();
    });
  });

  describe('sequential validations', () => {
    it('handles multiple validations in sequence', async () => {
      vi.mocked(axios.get)
        .mockResolvedValueOnce({data: {}})
        .mockRejectedValueOnce(new Error('Not found'))
        .mockRejectedValueOnce(new Error('Not found'));
      const {result} = renderHook(() => useUsernameValidation(), {wrapper});
      act(() => {
        result.current.validateUsername('existingUser');
      });
      await waitFor(() => {
        expect(result.current.state).toBe('existing');
      });
      act(() => {
        result.current.validateUsername('newUser');
      });
      await waitFor(() => {
        expect(result.current.state).toBe('confirmed');
      });
    });
  });
});
