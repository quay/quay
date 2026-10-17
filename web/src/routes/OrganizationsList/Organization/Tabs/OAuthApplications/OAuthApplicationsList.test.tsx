import {render, screen} from 'src/test-utils';
import OAuthApplicationsList from './OAuthApplicationsList';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
);

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

vi.mock('src/hooks/UseOAuthApplications', () => ({
  useFetchOAuthApplications: () => ({
    oauthApplications: [],
    loading: false,
    error: null,
  }),
  useBulkDeleteOAuthApplications: () => ({
    bulkDeleteOAuthApplications: vi.fn(),
    errorBulkDeleteOAuthApplications: null,
    successBulkDeleteOAuthApplications: false,
  }),
}));

vi.mock('./CreateOAuthApplicationModal', () => ({
  default: () => null,
}));
vi.mock('./OAuthApplicationActionsKebab', () => ({
  default: () => null,
}));
vi.mock('./OAuthApplicationsToolbar', () => ({
  default: ({children}: {children?: React.ReactNode}) => <div>{children}</div>,
}));
vi.mock('./ManageOAuthApplicationModal', () => ({
  default: () => null,
}));

describe('OAuthApplicationsList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
  });

  it('shows create button in empty state for non-readonly user', () => {
    render(<OAuthApplicationsList orgName="myorg" />);
    expect(
      screen.getByTestId('create-oauth-application-button'),
    ).toBeInTheDocument();
  });

  it('hides create button in empty state for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(<OAuthApplicationsList orgName="myorg" />);
    expect(
      screen.queryByTestId('create-oauth-application-button'),
    ).not.toBeInTheDocument();
  });
});
