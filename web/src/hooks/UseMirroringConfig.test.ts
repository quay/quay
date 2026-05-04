import {renderHook, act, waitFor} from '@testing-library/react';
import {useMirroringConfig} from './UseMirroringConfig';
import {
  getMirrorConfig,
  createMirrorConfig,
} from 'src/resources/MirroringResource';

vi.mock('src/resources/MirroringResource', () => ({
  getMirrorConfig: vi.fn(),
  createMirrorConfig: vi.fn(),
  updateMirrorConfig: vi.fn(),
  timestampToISO: vi.fn(() => '2024-01-01T00:00:00Z'),
  timestampFromISO: vi.fn(() => 1704067200),
}));

vi.mock('src/libs/utils', () => ({
  convertToSeconds: vi.fn((value: number) => value * 3600),
  convertFromSeconds: vi.fn(() => ({value: 1, unit: 'hours'})),
  formatDateForInput: vi.fn(() => '2024-01-01T00:00'),
}));

vi.mock('src/resources/UserResource', () => ({
  EntityKind: {user: 'user', team: 'team'},
}));

describe('UseMirroringConfig', () => {
  const mockReset = vi.fn();
  const mockSetSelectedRobot = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads existing config when repoState is MIRROR', async () => {
    const mockConfig = {
      is_enabled: true,
      external_reference: 'docker.io/library/nginx',
      root_rule: {rule_kind: 'tag_glob_csv', rule_value: ['latest', 'stable']},
      sync_start_date: '2024-01-01T00:00:00Z',
      sync_interval: 3600,
      robot_username: 'myorg+mirror_bot',
      external_registry_username: '',
      external_registry_config: {
        verify_tls: true,
        unsigned_images: false,
        proxy: {http_proxy: '', https_proxy: '', no_proxy: ''},
      },
      skopeo_timeout_interval: 300,
      architecture_filter: [],
    };
    vi.mocked(getMirrorConfig).mockResolvedValueOnce(mockConfig as any);

    const {result} = renderHook(() =>
      useMirroringConfig(
        'myorg',
        'myrepo',
        'MIRROR',
        mockReset,
        mockSetSelectedRobot,
      ),
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(getMirrorConfig).toHaveBeenCalledWith('myorg', 'myrepo');
    expect(result.current.config).toEqual(mockConfig);
    expect(result.current.error).toBeNull();
    expect(mockReset).toHaveBeenCalled();
    expect(mockSetSelectedRobot).toHaveBeenCalledWith(
      expect.objectContaining({name: 'myorg+mirror_bot', is_robot: true}),
    );
  });

  it('does not fetch config when repoState is not MIRROR', async () => {
    const {result} = renderHook(() =>
      useMirroringConfig(
        'myorg',
        'myrepo',
        'NORMAL',
        mockReset,
        mockSetSelectedRobot,
      ),
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(getMirrorConfig).not.toHaveBeenCalled();
    expect(result.current.config).toBeNull();
  });

  it('handles 404 by setting config to null without error', async () => {
    vi.mocked(getMirrorConfig).mockRejectedValueOnce({
      response: {status: 404},
    });

    const {result} = renderHook(() =>
      useMirroringConfig(
        'myorg',
        'myrepo',
        'MIRROR',
        mockReset,
        mockSetSelectedRobot,
      ),
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.config).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('sets error on non-404 fetch failure', async () => {
    vi.mocked(getMirrorConfig).mockRejectedValueOnce(
      new Error('Network error'),
    );

    const {result} = renderHook(() =>
      useMirroringConfig(
        'myorg',
        'myrepo',
        'MIRROR',
        mockReset,
        mockSetSelectedRobot,
      ),
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe('Network error');
  });

  it('submitConfig calls createMirrorConfig when no existing config', async () => {
    vi.mocked(getMirrorConfig).mockRejectedValueOnce({
      response: {status: 404},
    });
    vi.mocked(createMirrorConfig).mockResolvedValueOnce(undefined);

    const {result} = renderHook(() =>
      useMirroringConfig(
        'myorg',
        'myrepo',
        'MIRROR',
        mockReset,
        mockSetSelectedRobot,
      ),
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.submitConfig({
        isEnabled: true,
        externalReference: 'docker.io/library/nginx',
        tags: 'latest, stable',
        syncStartDate: '2024-01-01T00:00',
        syncValue: '1',
        syncUnit: 'hours',
        robotUsername: 'myorg+bot',
        username: '',
        password: '',
        verifyTls: true,
        httpProxy: '',
        httpsProxy: '',
        noProxy: '',
        unsignedImages: false,
        skopeoTimeoutInterval: 300,
        architectureFilter: [],
      });
    });

    expect(createMirrorConfig).toHaveBeenCalledWith(
      'myorg',
      'myrepo',
      expect.objectContaining({
        is_enabled: true,
        external_reference: 'docker.io/library/nginx',
        root_rule: {
          rule_kind: 'tag_glob_csv',
          rule_value: ['latest', 'stable'],
        },
      }),
    );
  });
});
