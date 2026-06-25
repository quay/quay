import {renderHook, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useManifestByDigest} from './UseManifestByDigest';
import {getManifestByDigest} from 'src/resources/TagResource';

vi.mock('src/resources/TagResource', () => ({
  getManifestByDigest: vi.fn(),
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

describe('useManifestByDigest', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('fetches manifest when all params provided', async () => {
    const mockManifest = {digest: 'sha256:abc', layers: []};
    vi.mocked(getManifestByDigest).mockResolvedValueOnce(mockManifest as any);
    const {result} = renderHook(
      () => useManifestByDigest('myorg', 'myrepo', 'sha256:abc'),
      {wrapper},
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(mockManifest);
  });

  it('does not fetch when digest is empty', () => {
    renderHook(() => useManifestByDigest('myorg', 'myrepo', ''), {wrapper});
    expect(getManifestByDigest).not.toHaveBeenCalled();
  });
});
