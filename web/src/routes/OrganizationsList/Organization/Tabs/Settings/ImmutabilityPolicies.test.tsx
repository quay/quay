import {render, screen} from 'src/test-utils';
import ImmutabilityPolicies from './ImmutabilityPolicies';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
);

const mockUseImmutabilityPolicies = vi.hoisted(() =>
  vi.fn(() => ({
    policies: [],
    isLoading: false,
    error: null,
    createPolicy: vi.fn(),
    updatePolicy: vi.fn(),
    deletePolicy: vi.fn(),
  })),
);

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

vi.mock('src/hooks/UseNamespaceImmutabilityPolicies', () => ({
  useNamespaceImmutabilityPolicies: mockUseImmutabilityPolicies,
}));

vi.mock('src/components/ImmutabilityPolicyForm', () => ({
  default: () => <div data-testid="policy-form-stub" />,
}));

describe('ImmutabilityPolicies', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
    mockUseImmutabilityPolicies.mockReturnValue({
      policies: [],
      isLoading: false,
      error: null,
      createPolicy: vi.fn(),
      updatePolicy: vi.fn(),
      deletePolicy: vi.fn(),
    });
  });

  it('shows add policy button for non-readonly user in empty state', () => {
    render(<ImmutabilityPolicies organizationName="myorg" />);
    expect(screen.getByText('Add Policy')).toBeInTheDocument();
  });

  it('hides add policy button for readonly superuser in empty state', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(<ImmutabilityPolicies organizationName="myorg" />);
    expect(screen.queryByText('Add Policy')).not.toBeInTheDocument();
  });

  it('shows add policy button with existing policies', () => {
    mockUseImmutabilityPolicies.mockReturnValue({
      policies: [{id: '1', tag_pattern: 'latest', enabled: true}],
      isLoading: false,
      error: null,
      createPolicy: vi.fn(),
      updatePolicy: vi.fn(),
      deletePolicy: vi.fn(),
    });
    render(<ImmutabilityPolicies organizationName="myorg" />);
    expect(screen.getByText('Add Policy')).toBeInTheDocument();
  });

  it('hides add policy and action buttons for readonly superuser with policies', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    mockUseImmutabilityPolicies.mockReturnValue({
      policies: [{id: '1', tag_pattern: 'latest', enabled: true}],
      isLoading: false,
      error: null,
      createPolicy: vi.fn(),
      updatePolicy: vi.fn(),
      deletePolicy: vi.fn(),
    });
    render(<ImmutabilityPolicies organizationName="myorg" />);
    expect(screen.queryByText('Add Policy')).not.toBeInTheDocument();
  });
});
