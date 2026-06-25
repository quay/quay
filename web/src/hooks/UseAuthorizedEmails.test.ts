import {renderHook, act, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useAuthorizedEmails} from './UseAuthorizedEmails';
import {
  fetchAuthorizedEmail,
  sendAuthorizedEmail,
} from 'src/resources/AuthorizedEmailResource';

vi.mock('src/resources/AuthorizedEmailResource', () => ({
  fetchAuthorizedEmail: vi.fn(),
  sendAuthorizedEmail: vi.fn(),
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

describe('useAuthorizedEmails', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('starts with polling=false', () => {
    const {result} = renderHook(() => useAuthorizedEmails('myorg', 'myrepo'), {
      wrapper,
    });
    expect(result.current.polling).toBe(false);
    expect(result.current.emailConfirmed).toBe(false);
  });

  it('starts polling when startPolling is called', () => {
    vi.mocked(fetchAuthorizedEmail).mockImplementation(
      () => new Promise(vi.fn()),
    );
    const {result} = renderHook(() => useAuthorizedEmails('myorg', 'myrepo'), {
      wrapper,
    });
    act(() => {
      result.current.startPolling('test@example.com');
    });
    expect(result.current.polling).toBe(true);
  });

  it('sends authorized email and reports success', async () => {
    vi.mocked(sendAuthorizedEmail).mockResolvedValueOnce(undefined);
    const {result} = renderHook(() => useAuthorizedEmails('myorg', 'myrepo'), {
      wrapper,
    });
    act(() => {
      result.current.sendAuthorizedEmail('test@example.com');
    });
    await waitFor(() =>
      expect(result.current.successSendingAuthorizedEmail).toBe(true),
    );
    expect(sendAuthorizedEmail).toHaveBeenCalledWith(
      'myorg',
      'myrepo',
      'test@example.com',
    );
  });
});
