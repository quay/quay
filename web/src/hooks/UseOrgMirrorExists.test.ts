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

function axiosError(status: number) {
  const err: any = new Error(`Request failed with status ${status}`);
  err._isAxiosError = true;
  err.response = {status};
  return err;
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

  it('returns isOrgMirrored=false on 404 (no mirror config)', async () => {
    vi.mocked(getOrgMirrorConfig).mockRejectedValueOnce(axiosError(404));
    const {result} = renderHook(() => useOrgMirrorExists('myorg'), {wrapper});
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.isOrgMirrored).toBe(false);
    expect(result.current.isError).toBe(false);
  });

  it('returns isOrgMirrored=false on 403 (PROJQUAY-11478: feature flag off)', async () => {
    vi.mocked(getOrgMirrorConfig).mockRejectedValueOnce(axiosError(403));
    const {result} = renderHook(() => useOrgMirrorExists('myorg'), {wrapper});
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.isOrgMirrored).toBe(false);
    expect(result.current.isError).toBe(false);
  });

  it('returns isOrgMirrored=false on 405 (endpoint not registered)', async () => {
    vi.mocked(getOrgMirrorConfig).mockRejectedValueOnce(axiosError(405));
    const {result} = renderHook(() => useOrgMirrorExists('myorg'), {wrapper});
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.isOrgMirrored).toBe(false);
    expect(result.current.isError).toBe(false);
  });

  it('returns isOrgMirrored=false on 400 (bad request)', async () => {
    vi.mocked(getOrgMirrorConfig).mockRejectedValueOnce(axiosError(400));
    const {result} = renderHook(() => useOrgMirrorExists('myorg'), {wrapper});
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.isOrgMirrored).toBe(false);
    expect(result.current.isError).toBe(false);
  });

  it('propagates 5xx errors as query errors', async () => {
    vi.mocked(getOrgMirrorConfig).mockRejectedValueOnce(axiosError(500));
    const {result} = renderHook(() => useOrgMirrorExists('myorg'), {wrapper});
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.isOrgMirrored).toBeUndefined();
  });

  it('propagates network errors (no response) as query errors', async () => {
    const networkError: any = new Error('Network Error');
    networkError._isAxiosError = true;
    vi.mocked(getOrgMirrorConfig).mockRejectedValueOnce(networkError);
    const {result} = renderHook(() => useOrgMirrorExists('myorg'), {wrapper});
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.isOrgMirrored).toBeUndefined();
  });

  it('does not fetch when enabled=false', () => {
    renderHook(() => useOrgMirrorExists('myorg', false), {wrapper});
    expect(getOrgMirrorConfig).not.toHaveBeenCalled();
  });
});
