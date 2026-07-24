import {render, screen} from 'src/test-utils';
import ProtectedRepositoryRoute from './ProtectedRepositoryRoute';

const mockUseCurrentUser = vi.hoisted(() =>
  vi.fn(() => ({user: null, loading: true})),
);

const mockUseRepository = vi.hoisted(() => vi.fn(() => ({repoDetails: null})));

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: mockUseCurrentUser,
}));

vi.mock('src/hooks/UseRepository', () => ({
  useRepository: mockUseRepository,
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

vi.mock('./RepositoryTagRouter', () => ({
  default: () => <div data-testid="repo-tag-router">RepositoryTagRouter</div>,
}));

vi.mock('src/components/header/QuayHeader', () => ({
  QuayHeader: () => <div data-testid="quay-header">Header</div>,
}));

vi.mock('src/components/sidebar/QuaySidebar', () => ({
  QuaySidebar: () => <div data-testid="quay-sidebar">Sidebar</div>,
}));

describe('ProtectedRepositoryRoute', () => {
  it('returns null while user is loading', () => {
    mockUseCurrentUser.mockReturnValue({user: null, loading: true});

    const {container} = render(<ProtectedRepositoryRoute />);
    expect(container.innerHTML).toBe('');
  });

  it('renders content without Page wrapper for authenticated users', async () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: 'testuser', anonymous: false},
      loading: false,
    });

    render(<ProtectedRepositoryRoute />);
    expect(await screen.findByTestId('repo-tag-router')).toBeInTheDocument();
    expect(screen.queryByTestId('quay-header')).not.toBeInTheDocument();
    expect(screen.queryByTestId('quay-sidebar')).not.toBeInTheDocument();
  });

  it('returns null for anonymous user when repo details not loaded', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: '', anonymous: true},
      loading: false,
    });
    mockUseRepository.mockReturnValue({repoDetails: null});

    const {container} = render(<ProtectedRepositoryRoute />);
    expect(container.innerHTML).toBe('');
  });

  it('renders Page wrapper with header/sidebar for anonymous user with repo details', async () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: '', anonymous: true},
      loading: false,
    });
    mockUseRepository.mockReturnValue({
      repoDetails: {name: 'testrepo', namespace: 'testorg'},
    });

    render(<ProtectedRepositoryRoute />);
    expect(await screen.findByTestId('repo-tag-router')).toBeInTheDocument();
    expect(screen.getByTestId('quay-header')).toBeInTheDocument();
    expect(screen.getByTestId('quay-sidebar')).toBeInTheDocument();
  });

  it('passes correct args to useRepository for anonymous users', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: '', anonymous: true},
      loading: false,
    });

    render(<ProtectedRepositoryRoute />);
    expect(mockUseRepository).toHaveBeenCalledWith('testorg', 'testrepo', true);
  });

  it('does not fetch repo for authenticated users', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: 'testuser', anonymous: false},
      loading: false,
    });

    render(<ProtectedRepositoryRoute />);
    expect(mockUseRepository).toHaveBeenCalledWith(
      'testorg',
      'testrepo',
      false,
    );
  });
});
