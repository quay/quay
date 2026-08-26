import {render, screen} from 'src/test-utils';
import RepositoryDetails from './RepositoryDetails';

const mockUseCurrentUser = vi.hoisted(() =>
  vi.fn(() => ({user: {username: 'testuser'}, loading: false})),
);

const mockUseRepository = vi.hoisted(() =>
  vi.fn(() => ({
    repoDetails: {name: 'testrepo', namespace: 'testorg', can_admin: true},
    errorLoadingRepoDetails: null,
  })),
);

const mockIsRedirecting = vi.hoisted(() => vi.fn(() => false));

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: mockUseCurrentUser,
}));

vi.mock('src/hooks/UseRepository', () => ({
  useRepository: mockUseRepository,
}));

vi.mock('src/libs/axios', () => ({
  default: {get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn()},
  isRedirecting: mockIsRedirecting,
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({features: {}, config: {}}),
}));

vi.mock('src/hooks/UseTeams', () => ({
  useFetchTeams: () => ({teams: []}),
}));

vi.mock('src/components/breadcrumb/Breadcrumb', () => ({
  QuayBreadcrumb: () => null,
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useLocation: () => ({
      pathname: '/repository/testorg/testrepo',
      search: '',
      hash: '',
    }),
    useNavigate: () => vi.fn(),
    useSearchParams: () => [new URLSearchParams(), vi.fn()],
    Link: ({children, to}: {children: React.ReactNode; to: string}) => (
      <a href={to}>{children}</a>
    ),
  };
});

vi.mock('src/libs/utils', async () => {
  const actual = await vi.importActual('src/libs/utils');
  return {
    ...actual,
    parseOrgNameFromUrl: () => 'testorg',
    parseRepoNameFromUrl: () => 'testrepo',
  };
});

vi.mock('./Tags/TagsList', () => ({default: () => <div>Tags</div>}));
vi.mock('./TagHistory/TagHistory', () => ({default: () => <div>History</div>}));
vi.mock('./Builds/Builds', () => ({default: () => <div>Builds</div>}));
vi.mock('./Settings/Settings', () => ({default: () => <div>Settings</div>}));
vi.mock('./Settings/NotificationsCreateNotification', () => ({
  default: () => null,
}));
vi.mock('./Settings/PermissionsAddPermission', () => ({
  default: () => null,
}));
vi.mock('./Information/Information', () => ({
  default: () => <div>Information</div>,
}));
vi.mock('../UsageLogs/UsageLogs', () => ({default: () => <div>Logs</div>}));
vi.mock('./Mirroring/Mirroring', () => ({Mirroring: () => null}));
vi.mock('src/components/modals/CreateRobotAccountModal', () => ({
  default: () => null,
}));
vi.mock(
  '../OrganizationsList/Organization/Tabs/DefaultPermissions/createPermissionDrawer/CreateTeamModal',
  () => ({CreateTeamModal: () => null}),
);
vi.mock('../RepositoriesList/RobotAccountsList', () => ({
  RepoPermissionDropdownItems: [],
}));

describe('RepositoryDetails', () => {
  it('returns null when isRedirecting is true', () => {
    mockIsRedirecting.mockReturnValue(true);

    const {container} = render(<RepositoryDetails />);
    expect(container.innerHTML).toBe('');
  });

  it('returns null for anonymous user when repo details not loaded', () => {
    mockIsRedirecting.mockReturnValue(false);
    mockUseCurrentUser.mockReturnValue({
      user: {username: '', anonymous: true},
      loading: false,
    });
    mockUseRepository.mockReturnValue({
      repoDetails: null,
      errorLoadingRepoDetails: null,
    });

    const {container} = render(<RepositoryDetails />);
    expect(container.innerHTML).toBe('');
  });

  it('renders repo title for authenticated user', () => {
    mockIsRedirecting.mockReturnValue(false);
    mockUseCurrentUser.mockReturnValue({
      user: {username: 'testuser', anonymous: false},
      loading: false,
    });
    mockUseRepository.mockReturnValue({
      repoDetails: {
        name: 'testrepo',
        namespace: 'testorg',
        can_admin: true,
        can_write: true,
      },
      errorLoadingRepoDetails: null,
    });

    render(<RepositoryDetails />);
    expect(screen.getByTestId('repo-title')).toHaveTextContent('testrepo');
  });

  it('passes shouldFetchRepo based on userLoading state', () => {
    mockIsRedirecting.mockReturnValue(false);
    mockUseCurrentUser.mockReturnValue({
      user: null,
      loading: true,
    });

    render(<RepositoryDetails />);
    expect(mockUseRepository).toHaveBeenCalledWith(
      'testorg',
      'testrepo',
      false,
    );
  });

  it('renders for anonymous user when repo details are available', () => {
    mockIsRedirecting.mockReturnValue(false);
    mockUseCurrentUser.mockReturnValue({
      user: {username: '', anonymous: true},
      loading: false,
    });
    mockUseRepository.mockReturnValue({
      repoDetails: {
        name: 'testrepo',
        namespace: 'testorg',
        can_admin: false,
        can_write: false,
      },
      errorLoadingRepoDetails: null,
    });

    render(<RepositoryDetails />);
    expect(screen.getByTestId('repo-title')).toHaveTextContent('testrepo');
  });
});
