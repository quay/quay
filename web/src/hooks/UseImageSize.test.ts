import {renderHook, waitFor} from '@testing-library/react';
import {useImageSize} from './UseImageSize';
import {getManifestByDigest} from 'src/resources/TagResource';

vi.mock('src/resources/TagResource', () => ({
  getManifestByDigest: vi.fn(),
}));

describe('useImageSize', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('calculates total size from manifest layers', async () => {
    vi.mocked(getManifestByDigest).mockResolvedValueOnce({
      layers: [
        {compressed_size: 100000},
        {compressed_size: 200000},
        {compressed_size: 50000},
      ],
    } as any);
    const {result} = renderHook(() =>
      useImageSize('myorg', 'myrepo', 'sha256:abc'),
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.size).toBe(350000);
    expect(result.current.err).toBe(false);
  });

  it('returns size=0 when manifest has no layers', async () => {
    vi.mocked(getManifestByDigest).mockResolvedValueOnce({
      layers: null,
    } as any);
    const {result} = renderHook(() =>
      useImageSize('myorg', 'myrepo', 'sha256:abc'),
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.size).toBe(0);
  });

  it('sets err=true on fetch failure', async () => {
    vi.mocked(getManifestByDigest).mockRejectedValueOnce(
      new Error('Not found'),
    );
    const {result} = renderHook(() =>
      useImageSize('myorg', 'myrepo', 'sha256:abc'),
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.err).toBe(true);
  });
});
