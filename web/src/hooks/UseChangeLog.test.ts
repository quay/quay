import {renderHook, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useChangeLog} from './UseChangeLog';
import {fetchChangeLog} from 'src/resources/ChangeLogResource';

vi.mock('src/resources/ChangeLogResource', () => ({
  fetchChangeLog: vi.fn(),
}));

function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    QueryClientProvider,
    {client: queryClient},
    children,
  );
}

describe('useChangeLog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches change log and exposes changeLog', async () => {
    const mockLog = [{version: '1.0', changes: ['initial release']}];
    vi.mocked(fetchChangeLog).mockResolvedValueOnce(mockLog as any);
    const {result} = renderHook(() => useChangeLog(), {wrapper});
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.changeLog).toEqual(mockLog);
  });

  it('exposes error on failure', async () => {
    vi.mocked(fetchChangeLog).mockRejectedValueOnce(new Error('fetch failed'));
    const {result} = renderHook(() => useChangeLog(), {wrapper});
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
