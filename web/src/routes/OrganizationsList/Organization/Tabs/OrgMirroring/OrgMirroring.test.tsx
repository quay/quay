import {render, screen} from 'src/test-utils';
import {OrgMirroring} from './OrgMirroring';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
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

const mockUseOrgMirroringConfig = vi.hoisted(() =>
  vi.fn(() => ({
    config: mockConfig,
    isLoading: false,
    error: null,
    isSyncingNow: false,
    isCancellingSync: false,
    isOrgSyncing: false,
    isVerifying: false,
    submitConfig: vi.fn(),
    handleSyncNow: vi.fn(),
    handleToggleEnabled: vi.fn(),
    handleCancelSync: vi.fn(),
    handleVerifyConnection: vi.fn(),
    setConfig: vi.fn(),
    invalidateConfig: vi.fn(),
  })),
);

const mockUseOrgMirroringForm = vi.hoisted(() =>
  vi.fn(() => ({
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
  })),
);

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

vi.mock('src/hooks/UseOrgMirroringConfig', () => ({
  useOrgMirroringConfig: mockUseOrgMirroringConfig,
}));

vi.mock('src/hooks/UseOrgMirroringForm', () => ({
  useOrgMirroringForm: mockUseOrgMirroringForm,
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
  return {
    ...actual,
    deleteOrgMirrorConfig: vi.fn(),
  };
});

vi.mock('./OrgMirroringConfiguration', () => ({
  OrgMirroringConfiguration: (props: Record<string, unknown>) => (
    <div data-testid="org-mirror-config">
      <button
        data-testid="stub-sync-now"
        disabled={!props.onSyncNow}
        onClick={props.onSyncNow as () => void}
      >
        Sync Now
      </button>
      <button data-testid="stub-toggle" disabled={!props.onToggleEnabled}>
        Toggle
      </button>
    </div>
  ),
}));

vi.mock('./OrgMirroringCredentials', () => ({
  OrgMirroringCredentials: () => null,
}));

vi.mock('./OrgMirroringFilters', () => ({
  OrgMirroringFilters: () => null,
}));

vi.mock('./OrgMirroringAdvancedSettings', () => ({
  OrgMirroringAdvancedSettings: () => null,
}));

vi.mock('./OrgMirroringStatus', () => ({
  OrgMirroringStatus: (props: Record<string, unknown>) => (
    <div data-testid="org-mirror-status">
      <button data-testid="stub-cancel-sync" disabled={!props.onCancelSync}>
        Cancel
      </button>
      <button data-testid="stub-verify" disabled={!props.onVerifyConnection}>
        Verify
      </button>
    </div>
  ),
}));

vi.mock('./OrgMirroringRepos', () => ({
  OrgMirroringRepos: () => null,
}));

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

  it('disables submit button for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(<OrgMirroring orgName="myorg" />);
    expect(screen.getByTestId('submit-button')).toBeDisabled();
  });

  it('disables delete button for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(<OrgMirroring orgName="myorg" />);
    expect(screen.getByTestId('delete-mirror-button')).toBeDisabled();
  });

  it('enables submit button for non-readonly superuser', () => {
    render(<OrgMirroring orgName="myorg" />);
    expect(screen.getByTestId('submit-button')).toBeInTheDocument();
  });
});
