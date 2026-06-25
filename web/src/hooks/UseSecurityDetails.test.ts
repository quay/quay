import {renderHook, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useSecurityDetails} from './UseSecurityDetails';
import {getSecurityDetails} from 'src/resources/TagResource';

vi.mock('src/resources/TagResource', () => ({
  getSecurityDetails: vi.fn(),
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

describe('useSecurityDetails', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('fetches security details when all params are provided', async () => {
    const mockDetails = {data: {Layer: {Features: []}}, status: 'scanned'};
    vi.mocked(getSecurityDetails).mockResolvedValueOnce(mockDetails as any);
    const {result} = renderHook(
      () => useSecurityDetails('myorg', 'myrepo', 'sha256:abc'),
      {wrapper},
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockDetails);
  });

  it('does not fetch when org is empty', () => {
    renderHook(() => useSecurityDetails('', 'myrepo', 'sha256:abc'), {wrapper});
    expect(getSecurityDetails).not.toHaveBeenCalled();
  });
});
