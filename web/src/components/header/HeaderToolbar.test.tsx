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

describe('HeaderToolbar', () => {
  it('shows sign in button for anonymous users', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: '', anonymous: true},
    });

    render(<HeaderToolbar toggleDrawer={vi.fn()} />);
    expect(screen.getByText('Sign In')).toBeInTheDocument();
    expect(screen.queryByTestId('notification-bell')).not.toBeInTheDocument();
  });

  it('shows notification badge for authenticated users', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: 'testuser', anonymous: false},
    });

    render(<HeaderToolbar toggleDrawer={vi.fn()} />);
    expect(screen.getByTestId('notification-bell')).toBeInTheDocument();
    expect(screen.queryByText('Sign In')).not.toBeInTheDocument();
  });
});
