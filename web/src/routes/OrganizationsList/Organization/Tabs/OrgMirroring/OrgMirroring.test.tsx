import {render, screen, userEvent} from 'src/test-utils';
import {OrgMirroring} from './OrgMirroring';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
);

const mockHandleSyncNow = vi.hoisted(() =>
  vi.fn().mockResolvedValue(undefined),
);
const mockHandleToggleEnabled = vi.hoisted(() =>
  vi.fn().mockResolvedValue(undefined),
);
const mockHandleCancelSync = vi.hoisted(() =>
  vi.fn().mockResolvedValue(undefined),
);
const mockHandleVerifyConnection = vi.hoisted(() =>
  vi.fn().mockResolvedValue({success: true, message: 'OK'}),
);

const mockConfig = vi.hoisted(() => ({
  id: 1,
  is_enabled: true,
  external_registry: 'quay.io',
  external_namespace: 'test',
  sync_interval: 3600,
  sync_start_date: '2026-01-01T00:00:00Z',
  sync_expiration_date: null,
  robot_username: 'org+robot',
  root_rule: {rule_kind: 'tag_glob_csv', rule_value: ['*']},
  external_registry_config: {},
  repo_sync_status_counts: {SYNCING: 0, SYNC_NOW: 0, SUCCESS: 5},
}));

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

vi.mock('src/hooks/UseOrgMirroringConfig', () => ({
  useOrgMirroringConfig: () => ({
    config: mockConfig,
    isLoading: false,
    error: null,
    isSyncingNow: false,
    isCancellingSync: false,
    isOrgSyncing: false,
    isVerifying: false,
    submitConfig: vi.fn(),
    handleSyncNow: mockHandleSyncNow,
    handleToggleEnabled: mockHandleToggleEnabled,
    handleCancelSync: mockHandleCancelSync,
    handleVerifyConnection: mockHandleVerifyConnection,
    setConfig: vi.fn(),
    invalidateConfig: vi.fn(),
  }),
}));

vi.mock('src/hooks/UseOrgMirroringForm', () => ({
  useOrgMirroringForm: () => ({
    control: {},
    errors: {},
    isEnabled: true,
    isValid: true,
    isDirty: false,
    handleSubmit: vi.fn((fn) => fn),
    reset: vi.fn(),
    setValue: vi.fn(),
    selectedRobot: null,
    setSelectedRobot: vi.fn(),
    handleRobotSelect: vi.fn(),
    isCreateRobotModalOpen: false,
    setIsCreateRobotModalOpen: vi.fn(),
  }),
  defaultFormValues: {},
}));

vi.mock('src/hooks/useRobotAccounts', () => ({
  useFetchRobotAccounts: () => ({robots: [], isLoadingRobots: false}),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({config: {ROBOTS_DISALLOW: false}}),
}));

vi.mock('src/resources/OrgMirrorResource', async () => {
  const actual = await vi.importActual<
    typeof import('src/resources/OrgMirrorResource')
  >('src/resources/OrgMirrorResource');
  return {...actual, deleteOrgMirrorConfig: vi.fn()};
});

// Stubs that capture and expose callback props via clickable buttons
vi.mock('./OrgMirroringConfiguration', () => ({
  OrgMirroringConfiguration: (props: Record<string, unknown>) => (
    <div data-testid="org-mirror-config">
      <button
        data-testid="stub-sync-now"
        disabled={!props.onSyncNow}
        onClick={() => (props.onSyncNow as () => Promise<void>)?.()}
      >
        Sync Now
      </button>
      <button
        data-testid="stub-toggle"
        disabled={!props.onToggleEnabled}
        onClick={() =>
          (
            props.onToggleEnabled as (
              c: boolean,
              o: (v: boolean) => void,
            ) => Promise<void>
          )?.(true, vi.fn())
        }
      >
        Toggle
      </button>
    </div>
  ),
}));

vi.mock('./OrgMirroringCredentials', () => ({
  OrgMirroringCredentials: () => null,
}));
vi.mock('./OrgMirroringFilters', () => ({OrgMirroringFilters: () => null}));
vi.mock('./OrgMirroringAdvancedSettings', () => ({
  OrgMirroringAdvancedSettings: () => null,
}));

vi.mock('./OrgMirroringStatus', () => ({
  OrgMirroringStatus: (props: Record<string, unknown>) => (
    <div data-testid="org-mirror-status">
      <button
        data-testid="stub-cancel-sync"
        disabled={!props.onCancelSync}
        onClick={() => (props.onCancelSync as () => Promise<void>)?.()}
      >
        Cancel
      </button>
      <button
        data-testid="stub-verify"
        disabled={!props.onVerifyConnection}
        onClick={() => (props.onVerifyConnection as () => Promise<void>)?.()}
      >
        Verify
      </button>
    </div>
  ),
}));

vi.mock('./OrgMirroringRepos', () => ({OrgMirroringRepos: () => null}));
vi.mock('./CreateRobotModalWrapper', () => ({
  CreateRobotModalWrapper: () => null,
}));

vi.mock('react-router-dom', async () => {
  const actual =
    await vi.importActual<typeof import('react-router-dom')>(
      'react-router-dom',
    );
  return {
    ...actual,
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
  };
});

describe('OrgMirroring', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
    mockHandleSyncNow.mockResolvedValue(undefined);
    mockHandleToggleEnabled.mockResolvedValue(undefined);
    mockHandleCancelSync.mockResolvedValue(undefined);
    mockHandleVerifyConnection.mockResolvedValue({
      success: true,
      message: 'OK',
    });
  });

  it('renders the form when config exists', () => {
    render(<OrgMirroring orgName="myorg" />);
    expect(screen.getByTestId('org-mirror-form')).toBeInTheDocument();
  });

  it('passes callbacks when not readonly superuser', () => {
    render(<OrgMirroring orgName="myorg" />);
    expect(screen.getByTestId('stub-sync-now')).not.toBeDisabled();
    expect(screen.getByTestId('stub-toggle')).not.toBeDisabled();
    expect(screen.getByTestId('stub-cancel-sync')).not.toBeDisabled();
    expect(screen.getByTestId('stub-verify')).not.toBeDisabled();
  });

  it('passes undefined callbacks when readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(<OrgMirroring orgName="myorg" />);
    expect(screen.getByTestId('stub-sync-now')).toBeDisabled();
    expect(screen.getByTestId('stub-toggle')).toBeDisabled();
    expect(screen.getByTestId('stub-cancel-sync')).toBeDisabled();
    expect(screen.getByTestId('stub-verify')).toBeDisabled();
  });

  it('disables submit and delete buttons for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(<OrgMirroring orgName="myorg" />);
    expect(screen.getByTestId('submit-button')).toBeDisabled();
    expect(screen.getByTestId('delete-mirror-button')).toBeDisabled();
  });

  it('invokes handleSyncNow callback on click', async () => {
    const user = userEvent.setup();
    render(<OrgMirroring orgName="myorg" />);
    await user.click(screen.getByTestId('stub-sync-now'));
    expect(mockHandleSyncNow).toHaveBeenCalled();
  });

  it('invokes handleToggleEnabled callback on click', async () => {
    const user = userEvent.setup();
    render(<OrgMirroring orgName="myorg" />);
    await user.click(screen.getByTestId('stub-toggle'));
    expect(mockHandleToggleEnabled).toHaveBeenCalledWith(true);
  });

  it('invokes handleCancelSync callback on click', async () => {
    const user = userEvent.setup();
    render(<OrgMirroring orgName="myorg" />);
    await user.click(screen.getByTestId('stub-cancel-sync'));
    expect(mockHandleCancelSync).toHaveBeenCalled();
  });

  it('invokes handleVerifyConnection callback on click', async () => {
    const user = userEvent.setup();
    render(<OrgMirroring orgName="myorg" />);
    await user.click(screen.getByTestId('stub-verify'));
    expect(mockHandleVerifyConnection).toHaveBeenCalled();
  });

  it('handles verify connection failure result', async () => {
    mockHandleVerifyConnection.mockResolvedValue({
      success: false,
      message: 'Connection refused',
    });
    const user = userEvent.setup();
    render(<OrgMirroring orgName="myorg" />);
    await user.click(screen.getByTestId('stub-verify'));
    expect(mockHandleVerifyConnection).toHaveBeenCalled();
  });

  it('handles sync now error', async () => {
    mockHandleSyncNow.mockRejectedValue(new Error('sync failed'));
    const user = userEvent.setup();
    render(<OrgMirroring orgName="myorg" />);
    await user.click(screen.getByTestId('stub-sync-now'));
    expect(mockHandleSyncNow).toHaveBeenCalled();
  });

  it('handles cancel sync error', async () => {
    mockHandleCancelSync.mockRejectedValue(new Error('cancel failed'));
    const user = userEvent.setup();
    render(<OrgMirroring orgName="myorg" />);
    await user.click(screen.getByTestId('stub-cancel-sync'));
    expect(mockHandleCancelSync).toHaveBeenCalled();
  });

  it('handles verify connection error', async () => {
    mockHandleVerifyConnection.mockRejectedValue(new Error('verify failed'));
    const user = userEvent.setup();
    render(<OrgMirroring orgName="myorg" />);
    await user.click(screen.getByTestId('stub-verify'));
    expect(mockHandleVerifyConnection).toHaveBeenCalled();
  });
});
