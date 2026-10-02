import {render, screen} from 'src/test-utils';
import {OrgMirroringState} from './OrgMirroringState';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
);

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

vi.mock('src/hooks/UseOrgMirrorExists', () => ({
  useOrgMirrorExists: () => ({exists: false, isLoading: false}),
}));

vi.mock('src/hooks/UseProxyCache', () => ({
  useFetchProxyCacheConfig: () => ({
    proxyCacheConfig: null,
    isLoading: false,
    isError: false,
  }),
}));

vi.mock('src/hooks/UseNamespaceImmutabilityPolicies', () => ({
  useNamespaceImmutabilityPolicies: () => ({
    policies: [],
    isLoading: false,
  }),
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

describe('OrgMirroringState', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
  });

  it('renders the submit button', () => {
    render(<OrgMirroringState organizationName="myorg" />);
    expect(screen.getByText('Submit')).toBeInTheDocument();
  });

  it('disables submit button for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(<OrgMirroringState organizationName="myorg" />);
    expect(screen.getByText('Submit').closest('button')).toBeDisabled();
  });
});
