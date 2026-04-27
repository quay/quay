import {renderHook, waitFor} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {createTestQueryClient} from 'src/test-utils';
import {useOrgMirrorExists} from './UseOrgMirrorExists';
import {getOrgMirrorConfig} from 'src/resources/OrgMirrorResource';

vi.mock('src/resources/OrgMirrorResource', () => ({
  getOrgMirrorConfig: vi.fn(),
}));

vi.mock('axios', () => ({
  isAxiosError: (err: unknown) => (err as any)?._isAxiosError === true,
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

describe('useOrgMirrorExists', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('returns isOrgMirrored=true when config exists', async () => {
    vi.mocked(getOrgMirrorConfig).mockResolvedValueOnce({
      upstream_registry: 'registry.example.com',
    } as any);
    const {result} = renderHook(() => useOrgMirrorExists('myorg'), {wrapper});
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.isOrgMirrored).toBe(true);
  });

  it('does not fetch when enabled=false', () => {
    renderHook(() => useOrgMirrorExists('myorg', false), {wrapper});
    expect(getOrgMirrorConfig).not.toHaveBeenCalled();
  });
});
