import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {
  useGlobalMessages,
  useCreateGlobalMessage,
  useDeleteGlobalMessage,
} from './UseGlobalMessages';
import {
  fetchGlobalMessages,
  createGlobalMessage,
  deleteGlobalMessage,
} from 'src/resources/GlobalMessagesResource';

vi.mock('src/resources/GlobalMessagesResource', () => ({
  fetchGlobalMessages: vi.fn(),
  createGlobalMessage: vi.fn(),
  deleteGlobalMessage: vi.fn(),
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

describe('UseGlobalMessages', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('useGlobalMessages', () => {
    it('fetches global messages', async () => {
      const messages = [{uuid: 'm1', content: 'Maintenance', severity: 'info'}];
      vi.mocked(fetchGlobalMessages).mockResolvedValueOnce(messages as any);
      const {result} = renderHook(() => useGlobalMessages(), {wrapper});
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data).toEqual(messages);
    });
  });

  describe('useCreateGlobalMessage', () => {
    it('calls createGlobalMessage on mutate', async () => {
      vi.mocked(createGlobalMessage).mockResolvedValueOnce(undefined);
      const {result} = renderHook(() => useCreateGlobalMessage(), {wrapper});
      act(() => {
        result.current.mutate({
          content: 'New message',
          severity: 'info',
        } as any);
      });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(createGlobalMessage).toHaveBeenCalled();
    });
  });

  describe('useDeleteGlobalMessage', () => {
    it('calls deleteGlobalMessage on mutate', async () => {
      vi.mocked(deleteGlobalMessage).mockResolvedValueOnce(undefined);
      const {result} = renderHook(() => useDeleteGlobalMessage(), {wrapper});
      act(() => {
        result.current.mutate('m1');
      });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(deleteGlobalMessage).toHaveBeenCalledWith('m1');
    });
  });
});
