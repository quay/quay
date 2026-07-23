import {renderHook, act, waitFor} from '@testing-library/react';
import {useMirroringConfig} from './UseMirroringConfig';
import {
  getMirrorConfig,
  createMirrorConfig,
  updateMirrorConfig,
  timestampToISO,
  timestampFromISO,
  MirroringConfigResponse,
} from 'src/resources/MirroringResource';
import {MirroringFormData} from 'src/routes/RepositoryDetails/Mirroring/types';
import {
  convertToSeconds,
  convertFromSeconds,
  formatDateForInput,
} from 'src/libs/utils';

jest.mock('src/resources/MirroringResource', () => ({
  getMirrorConfig: jest.fn(),
  createMirrorConfig: jest.fn(),
  updateMirrorConfig: jest.fn(),
  timestampToISO: jest.fn(() => '2024-01-01T00:00:00Z'),
  timestampFromISO: jest.fn(() => 1704067200),
}));

jest.mock('src/libs/utils', () => ({
  convertToSeconds: jest.fn((value: number) => value * 3600),
  convertFromSeconds: jest.fn(() => ({value: 1, unit: 'hours'})),
  formatDateForInput: jest.fn(() => '2024-01-01T00:00'),
}));

jest.mock('src/resources/UserResource', () => ({
  EntityKind: {user: 'user', team: 'team'},
}));

const baseMirrorResponse: MirroringConfigResponse = {
  is_enabled: true,
  mirror_type: 'PULL',
  external_reference: 'quay.io/airlock/iam',
  external_registry_username: 'myuser',
  external_registry_config: {
    verify_tls: true,
    unsigned_images: false,
    proxy: {http_proxy: null, https_proxy: null, no_proxy: null},
  },
  sync_interval: 86400,
  sync_start_date: '2026-01-01T00:00:00Z',
  sync_expiration_date: null,
  sync_retries_remaining: 3,
  sync_status: 'SYNC_SUCCESS',
  root_rule: {rule_kind: 'tag_glob_csv', rule_value: ['latest']},
  robot_username: 'org+bot',
  skopeo_timeout_interval: 300,
  architecture_filter: [],
  last_sync: '',
  last_error: '',
  status_message: '',
};

const baseFormData: MirroringFormData = {
  isEnabled: true,
  externalReference: 'quay.io/airlock/iam',
  tags: 'latest',
  syncStartDate: '2026-01-01T00:00:00Z',
  syncValue: '24',
  syncUnit: 'hours',
  robotUsername: 'org+bot',
  username: 'myuser',
  password: '',
  verifyTls: true,
  httpProxy: '',
  httpsProxy: '',
  noProxy: '',
  unsignedImages: false,
  skopeoTimeoutInterval: 300,
  architectureFilter: [],
};

describe('UseMirroringConfig', () => {
  const mockReset = jest.fn();
  const mockSetSelectedRobot = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (timestampToISO as jest.Mock).mockImplementation(
      () => '2024-01-01T00:00:00Z',
    );
    (timestampFromISO as jest.Mock).mockImplementation(() => 1704067200);
    (convertToSeconds as jest.Mock).mockImplementation(
      (value: number) => value * 3600,
    );
    (convertFromSeconds as jest.Mock).mockImplementation(() => ({
      value: 1,
      unit: 'hours',
    }));
    (formatDateForInput as jest.Mock).mockImplementation(
      () => '2024-01-01T00:00',
    );
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
    jest.mocked(getMirrorConfig).mockResolvedValueOnce(mockConfig as any);

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
    expect(mockReset).toHaveBeenCalledWith(
      expect.objectContaining({
        isEnabled: true,
        externalReference: 'docker.io/library/nginx',
        tags: 'latest, stable',
        syncStartDate: '2024-01-01T00:00',
        syncValue: '1',
        syncUnit: 'hours',
        robotUsername: 'myorg+mirror_bot',
        username: '',
        password: '',
        verifyTls: true,
        httpProxy: '',
        httpsProxy: '',
        noProxy: '',
        unsignedImages: false,
        skopeoTimeoutInterval: 300,
      }),
    );
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
    jest.mocked(getMirrorConfig).mockRejectedValueOnce({
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
    jest.mocked(getMirrorConfig).mockRejectedValueOnce(
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
    jest.mocked(getMirrorConfig).mockRejectedValueOnce({
      response: {status: 404},
    });
    jest.mocked(createMirrorConfig).mockResolvedValueOnce(undefined);

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
        sync_interval: 3600,
        sync_start_date: '2024-01-01T00:00:00Z',
        robot_username: 'myorg+bot',
        skopeo_timeout_interval: 300,
        root_rule: {
          rule_kind: 'tag_glob_csv',
          rule_value: ['latest', 'stable'],
        },
        external_registry_config: {
          verify_tls: true,
          unsigned_images: false,
          proxy: {
            http_proxy: null,
            https_proxy: null,
            no_proxy: null,
          },
        },
      }),
    );
  });

  describe('submitConfig credential handling', () => {
    it('does not include credentials when updating config without a new password', async () => {
      jest.mocked(getMirrorConfig).mockResolvedValueOnce(baseMirrorResponse);
      jest.mocked(updateMirrorConfig).mockResolvedValueOnce(baseMirrorResponse);

      const {result} = renderHook(() =>
        useMirroringConfig(
          'org',
          'repo',
          'MIRROR',
          mockReset,
          mockSetSelectedRobot,
        ),
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.submitConfig({
          ...baseFormData,
          tags: '8.5.0',
          username: 'myuser',
          password: '',
        });
      });

      expect(updateMirrorConfig).toHaveBeenCalledTimes(1);
      const submittedConfig = jest.mocked(updateMirrorConfig).mock.calls[0][2];
      expect(submittedConfig).not.toHaveProperty('external_registry_username');
      expect(submittedConfig).not.toHaveProperty('external_registry_password');
    });

    it('includes credentials when updating config with a new password', async () => {
      jest.mocked(getMirrorConfig).mockResolvedValueOnce(baseMirrorResponse);
      jest.mocked(updateMirrorConfig).mockResolvedValueOnce(baseMirrorResponse);

      const {result} = renderHook(() =>
        useMirroringConfig(
          'org',
          'repo',
          'MIRROR',
          mockReset,
          mockSetSelectedRobot,
        ),
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.submitConfig({
          ...baseFormData,
          username: 'newuser',
          password: 'newpass',
        });
      });

      expect(updateMirrorConfig).toHaveBeenCalledTimes(1);
      const submittedConfig = jest.mocked(updateMirrorConfig).mock.calls[0][2];
      expect(submittedConfig.external_registry_username).toBe('newuser');
      expect(submittedConfig.external_registry_password).toBe('newpass');
    });

    it('sends only username when username changes without a new password', async () => {
      jest.mocked(getMirrorConfig).mockResolvedValueOnce(baseMirrorResponse);
      jest.mocked(updateMirrorConfig).mockResolvedValueOnce(baseMirrorResponse);

      const {result} = renderHook(() =>
        useMirroringConfig(
          'org',
          'repo',
          'MIRROR',
          mockReset,
          mockSetSelectedRobot,
        ),
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.submitConfig({
          ...baseFormData,
          username: 'differentuser',
          password: '',
        });
      });

      expect(updateMirrorConfig).toHaveBeenCalledTimes(1);
      const submittedConfig = jest.mocked(updateMirrorConfig).mock.calls[0][2];
      expect(submittedConfig.external_registry_username).toBe('differentuser');
      expect(submittedConfig).not.toHaveProperty('external_registry_password');
    });

    it('always includes credentials when creating new config', async () => {
      jest.mocked(getMirrorConfig).mockRejectedValueOnce({
        response: {status: 404},
      });
      jest.mocked(createMirrorConfig).mockResolvedValueOnce(baseMirrorResponse);

      const {result} = renderHook(() =>
        useMirroringConfig(
          'org',
          'repo',
          'MIRROR',
          mockReset,
          mockSetSelectedRobot,
        ),
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.submitConfig({
          ...baseFormData,
          username: 'myuser',
          password: '',
        });
      });

      expect(createMirrorConfig).toHaveBeenCalledTimes(1);
      const submittedConfig = jest.mocked(createMirrorConfig).mock.calls[0][2];
      expect(submittedConfig.external_registry_username).toBe('myuser');
      expect(submittedConfig.external_registry_password).toBeNull();
    });

    it('sends null username when creating config without credentials', async () => {
      jest.mocked(getMirrorConfig).mockRejectedValueOnce({
        response: {status: 404},
      });
      jest.mocked(createMirrorConfig).mockResolvedValueOnce(baseMirrorResponse);

      const {result} = renderHook(() =>
        useMirroringConfig(
          'org',
          'repo',
          'MIRROR',
          mockReset,
          mockSetSelectedRobot,
        ),
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.submitConfig({
          ...baseFormData,
          username: '',
          password: '',
        });
      });

      expect(createMirrorConfig).toHaveBeenCalledTimes(1);
      const submittedConfig = jest.mocked(createMirrorConfig).mock.calls[0][2];
      expect(submittedConfig.external_registry_username).toBeNull();
      expect(submittedConfig.external_registry_password).toBeNull();
    });

    it('sends null username when clearing username without password', async () => {
      jest.mocked(getMirrorConfig).mockResolvedValueOnce(baseMirrorResponse);
      jest.mocked(updateMirrorConfig).mockResolvedValueOnce(baseMirrorResponse);

      const {result} = renderHook(() =>
        useMirroringConfig(
          'org',
          'repo',
          'MIRROR',
          mockReset,
          mockSetSelectedRobot,
        ),
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.submitConfig({
          ...baseFormData,
          username: '',
          password: '',
        });
      });

      expect(updateMirrorConfig).toHaveBeenCalledTimes(1);
      const submittedConfig = jest.mocked(updateMirrorConfig).mock.calls[0][2];
      expect(submittedConfig.external_registry_username).toBeNull();
      expect(submittedConfig).not.toHaveProperty('external_registry_password');
    });

    it('handles config with null external_registry_username', async () => {
      const nullUsernameResponse = {
        ...baseMirrorResponse,
        external_registry_username: null,
      };
      jest.mocked(getMirrorConfig).mockResolvedValueOnce(nullUsernameResponse);
      jest.mocked(updateMirrorConfig).mockResolvedValueOnce(nullUsernameResponse);

      const {result} = renderHook(() =>
        useMirroringConfig(
          'org',
          'repo',
          'MIRROR',
          mockReset,
          mockSetSelectedRobot,
        ),
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.submitConfig({
          ...baseFormData,
          username: '',
          password: '',
        });
      });

      expect(updateMirrorConfig).toHaveBeenCalledTimes(1);
      const submittedConfig = jest.mocked(updateMirrorConfig).mock.calls[0][2];
      expect(submittedConfig).not.toHaveProperty('external_registry_username');
      expect(submittedConfig).not.toHaveProperty('external_registry_password');
    });
  });

  describe('config loading', () => {
    it('sets error on non-404 HTTP error response', async () => {
      jest.mocked(getMirrorConfig).mockRejectedValueOnce({
        response: {status: 500},
        message: 'Internal server error',
      });

      const {result} = renderHook(() =>
        useMirroringConfig(
          'org',
          'repo',
          'MIRROR',
          mockReset,
          mockSetSelectedRobot,
        ),
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.error).toBe('Internal server error');
    });

    it('uses fallback error message when error has no message', async () => {
      jest.mocked(getMirrorConfig).mockRejectedValueOnce({
        response: {status: 500},
      });

      const {result} = renderHook(() =>
        useMirroringConfig(
          'org',
          'repo',
          'MIRROR',
          mockReset,
          mockSetSelectedRobot,
        ),
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));
      expect(result.current.error).toBe('Failed to load mirror configuration');
    });

    it('populates defaults for null/missing response fields', async () => {
      const minimalResponse: MirroringConfigResponse = {
        ...baseMirrorResponse,
        external_reference: '',
        external_registry_username: null,
        external_registry_config:
          {} as MirroringConfigResponse['external_registry_config'],
        sync_start_date: '',
        robot_username: '',
        skopeo_timeout_interval: 0,
        architecture_filter: null as unknown as string[],
      };
      jest.mocked(getMirrorConfig).mockResolvedValueOnce(minimalResponse);

      renderHook(() =>
        useMirroringConfig(
          'org',
          'repo',
          'MIRROR',
          mockReset,
          mockSetSelectedRobot,
        ),
      );

      await waitFor(() => expect(mockReset).toHaveBeenCalled());
      const resetData = mockReset.mock.calls[0][0];
      expect(resetData.externalReference).toBe('');
      expect(resetData.username).toBe('');
      expect(resetData.robotUsername).toBe('');
      expect(resetData.verifyTls).toBe(true);
      expect(resetData.unsignedImages).toBe(false);
      expect(resetData.skopeoTimeoutInterval).toBe(300);
      expect(mockSetSelectedRobot).not.toHaveBeenCalled();
    });

    it('sets team entity kind for robot username without +', async () => {
      const teamResponse: MirroringConfigResponse = {
        ...baseMirrorResponse,
        robot_username: 'teambot',
      };
      jest.mocked(getMirrorConfig).mockResolvedValueOnce(teamResponse);

      renderHook(() =>
        useMirroringConfig(
          'org',
          'repo',
          'MIRROR',
          mockReset,
          mockSetSelectedRobot,
        ),
      );

      await waitFor(() => expect(mockSetSelectedRobot).toHaveBeenCalled());
      const robotEntity = mockSetSelectedRobot.mock.calls[0][0];
      expect(robotEntity.name).toBe('teambot');
      expect(robotEntity.is_robot).toBe(false);
      expect(robotEntity.kind).toBe('team');
    });
  });

  describe('submitConfig field handling', () => {
    it('uses current timestamp when syncStartDate is empty', async () => {
      jest.mocked(getMirrorConfig).mockRejectedValueOnce({
        response: {status: 404},
      });
      jest.mocked(createMirrorConfig).mockResolvedValueOnce(baseMirrorResponse);

      const {result} = renderHook(() =>
        useMirroringConfig(
          'org',
          'repo',
          'MIRROR',
          mockReset,
          mockSetSelectedRobot,
        ),
      );

      await waitFor(() => expect(result.current.isLoading).toBe(false));

      await act(async () => {
        await result.current.submitConfig({
          ...baseFormData,
          syncStartDate: '',
        });
      });

      const submittedConfig = jest.mocked(createMirrorConfig).mock.calls[0][2];
      expect(submittedConfig.sync_start_date).toBeDefined();
      expect(submittedConfig.sync_start_date).not.toBe('');
    });

  });
});
