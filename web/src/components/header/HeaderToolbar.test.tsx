import {MemoryRouter} from 'react-router-dom';
import {render, screen} from 'src/test-utils';
import {HeaderToolbar} from './HeaderToolbar';

const mockUseCurrentUser = vi.hoisted(() =>
  vi.fn(() => ({user: {username: 'testuser'}})),
);

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: mockUseCurrentUser,
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({
    features: {},
    config: {},
  }),
}));

vi.mock('src/hooks/useAppNotifications', () => ({
  useAppNotifications: () => ({
    notifications: [],
    unreadCount: 0,
    loading: false,
    dismissNotification: vi.fn(),
    refetch: vi.fn(),
  }),
}));

vi.mock('src/resources/AuthResource', () => ({
  GlobalAuthState: {csrfToken: null, bearerToken: null},
  logoutUser: vi.fn(),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

vi.mock('src/contexts/ThemeContext', () => ({
  useTheme: () => ({themePreference: 'light', setThemePreference: vi.fn()}),
  ThemePreference: {LIGHT: 'light', DARK: 'dark'},
}));

vi.mock('src/hooks/UseSearch', () => ({
  useSearchSuggestions: () => ({suggestions: [], isLoading: false}),
}));

function renderToolbar(route = '/organization') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <HeaderToolbar toggleDrawer={vi.fn()} />
    </MemoryRouter>,
  );
}

describe('HeaderToolbar', () => {
  it('shows sign in button for anonymous users', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: '', anonymous: true},
    });

    renderToolbar();
    expect(screen.getByText('Sign In')).toBeInTheDocument();
    expect(screen.queryByTestId('notification-bell')).not.toBeInTheDocument();
  });

  it('shows notification badge for authenticated users', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: 'testuser', anonymous: false},
    });

    renderToolbar();
    expect(screen.getByTestId('notification-bell')).toBeInTheDocument();
    expect(screen.queryByText('Sign In')).not.toBeInTheDocument();
  });

  it('renders the header search bar on ordinary pages', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: 'testuser', anonymous: false},
    });

    renderToolbar('/organization');
    expect(screen.getByTestId('header-search-item')).toBeInTheDocument();
  });

  it('hides the header search bar on the search page', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: 'testuser', anonymous: false},
    });

    renderToolbar('/search');
    expect(screen.queryByTestId('header-search-item')).not.toBeInTheDocument();
  });
});
