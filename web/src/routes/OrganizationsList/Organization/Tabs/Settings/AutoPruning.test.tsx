import {render, screen} from 'src/test-utils';
import AutoPruning from './AutoPruning';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
);

const mockUseNamespaceAutoPrunePolicies = vi.hoisted(() =>
  vi.fn(() => ({
    error: null,
    isSuccess: true,
    isLoading: false,
    nsPolicies: [],
    dataUpdatedAt: 0,
  })),
);

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

vi.mock('src/hooks/UseNamespaceAutoPrunePolicies', () => ({
  useNamespaceAutoPrunePolicies: mockUseNamespaceAutoPrunePolicies,
  useCreateNamespaceAutoPrunePolicy: () => ({
    createPolicy: vi.fn(),
    successCreatePolicy: false,
    errorCreatePolicy: false,
    errorCreatePolicyDetails: null,
  }),
  useUpdateNamespaceAutoPrunePolicy: () => ({
    updatePolicy: vi.fn(),
    successUpdatePolicy: false,
    errorUpdatePolicy: false,
    errorUpdatePolicyDetails: null,
  }),
  useDeleteNamespaceAutoPrunePolicy: () => ({
    deletePolicy: vi.fn(),
    successDeletePolicy: false,
    errorDeletePolicy: false,
    errorDeletePolicyDetails: null,
  }),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({config: {DEFAULT_NAMESPACE_AUTOPRUNE_POLICY: null}}),
}));

vi.mock('src/components/AutoPrunePolicyForm', () => ({
  default: () => <div data-testid="autoprune-form-stub" />,
}));

vi.mock(
  'src/routes/RepositoryDetails/Settings/RepositoryAutoPruningReadonlyPolicy',
  () => ({
    default: () => null,
  }),
);

describe('AutoPruning', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
    mockUseNamespaceAutoPrunePolicies.mockReturnValue({
      error: null,
      isSuccess: true,
      isLoading: false,
      nsPolicies: [],
      dataUpdatedAt: 0,
    });
  });

  it('shows add policy button for non-readonly user', () => {
    mockUseNamespaceAutoPrunePolicies.mockReturnValue({
      error: null,
      isSuccess: true,
      isLoading: false,
      nsPolicies: [{method: 'number_of_tags', value: 10, uuid: '1'}],
      dataUpdatedAt: 1,
    });
    render(<AutoPruning org="myorg" isUser={false} />);
    expect(screen.getByText('Add Policy')).toBeInTheDocument();
  });

  it('hides add policy button for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    mockUseNamespaceAutoPrunePolicies.mockReturnValue({
      error: null,
      isSuccess: true,
      isLoading: false,
      nsPolicies: [{method: 'number_of_tags', value: 10, uuid: '1'}],
      dataUpdatedAt: 1,
    });
    render(<AutoPruning org="myorg" isUser={false} />);
    expect(screen.queryByText('Add Policy')).not.toBeInTheDocument();
  });

  it('renders form for empty policies for non-readonly user', () => {
    render(<AutoPruning org="myorg" isUser={false} />);
    expect(screen.getByTestId('autoprune-form-stub')).toBeInTheDocument();
  });

  it('does not auto-open form for readonly superuser with empty policies', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(<AutoPruning org="myorg" isUser={false} />);
    expect(screen.queryByTestId('autoprune-form-stub')).not.toBeInTheDocument();
  });

  it('renders spinner while loading', () => {
    mockUseNamespaceAutoPrunePolicies.mockReturnValue({
      error: null,
      isSuccess: false,
      isLoading: true,
      nsPolicies: [],
      dataUpdatedAt: 0,
    });
    render(<AutoPruning org="myorg" isUser={false} />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });
});
