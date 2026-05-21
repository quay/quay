import {render, screen, userEvent} from 'src/test-utils';
import {HeaderToolbar} from './HeaderToolbar';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useAppNotifications} from 'src/hooks/useAppNotifications';
import {useTheme} from 'src/contexts/ThemeContext';

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: vi.fn(),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

vi.mock('src/hooks/useAppNotifications', () => ({
  useAppNotifications: vi.fn(),
}));

vi.mock('src/contexts/ThemeContext', () => ({
  useTheme: vi.fn(),
  ThemePreference: {LIGHT: 'LIGHT', DARK: 'DARK', AUTO: 'AUTO'},
}));

vi.mock('src/resources/AuthResource', () => ({
  logoutUser: vi.fn(),
  GlobalAuthState: {
    isLoggedIn: true,
    csrfToken: undefined,
    bearerToken: undefined,
  },
}));

vi.mock('src/components/Avatar', () => ({
  default: () => <div data-testid="mock-avatar" />,
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}));

vi.mock('src/components/errors/ErrorModal', () => ({
  default: () => null,
}));

const mockUseCurrentUser = vi.mocked(useCurrentUser);
const mockUseQuayConfig = vi.mocked(useQuayConfig);
const mockUseAppNotifications = vi.mocked(useAppNotifications);
const mockUseTheme = vi.mocked(useTheme);

beforeEach(() => {
  mockUseCurrentUser.mockReturnValue({
    user: {
      username: 'testuser',
      avatar: {name: 'testuser', hash: 'abc', color: '#fff', kind: 'user'},
    },
  } as ReturnType<typeof useCurrentUser>);
  mockUseQuayConfig.mockReturnValue({
    config: {REGISTRY_TITLE_SHORT: 'Quay', SERVER_HOSTNAME: 'quay.example.com'},
    features: {UI_V2: false},
  } as ReturnType<typeof useQuayConfig>);
  mockUseAppNotifications.mockReturnValue({
    unreadCount: 0,
    notifications: [],
    loading: false,
  } as ReturnType<typeof useAppNotifications>);
  mockUseTheme.mockReturnValue({
    themePreference: 'LIGHT' as ReturnType<typeof useTheme>['themePreference'],
    setThemePreference: vi.fn(),
    resolvedTheme: 'LIGHT' as ReturnType<typeof useTheme>['resolvedTheme'],
  });
});

describe('HeaderToolbar', () => {
  it('renders user menu toggle with username', () => {
    render(<HeaderToolbar toggleDrawer={vi.fn()} />);
    expect(screen.getByTestId('user-menu-toggle')).toBeInTheDocument();
    expect(screen.getByTestId('user-menu-toggle')).toHaveTextContent(
      'testuser',
    );
  });

  it('renders notification bell', () => {
    render(<HeaderToolbar toggleDrawer={vi.fn()} />);
    expect(screen.getByTestId('notification-bell')).toBeInTheDocument();
  });

  it('shows unread notification count', () => {
    mockUseAppNotifications.mockReturnValue({
      unreadCount: 5,
      notifications: [],
      loading: false,
    } as any);
    render(<HeaderToolbar toggleDrawer={vi.fn()} />);
    expect(screen.getByTestId('notification-bell')).toHaveTextContent('5');
  });

  it('calls toggleDrawer on notification bell click', async () => {
    const toggleDrawer = vi.fn();
    render(<HeaderToolbar toggleDrawer={toggleDrawer} />);
    await userEvent.click(screen.getByTestId('notification-bell'));
    expect(toggleDrawer).toHaveBeenCalled();
  });

  it('opens user menu on toggle click', async () => {
    render(<HeaderToolbar toggleDrawer={vi.fn()} />);
    await userEvent.click(screen.getByTestId('user-menu-toggle'));
    expect(screen.getByText('Account Settings')).toBeInTheDocument();
    expect(screen.getByText('Logout')).toBeInTheDocument();
  });

  it('shows sign in button when no user', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: ''},
    } as any);
    render(<HeaderToolbar toggleDrawer={vi.fn()} />);
    expect(
      screen.getByRole('button', {name: /sign in to quay/i}),
    ).toBeInTheDocument();
  });

  it('shows theme toggle in user menu', async () => {
    render(<HeaderToolbar toggleDrawer={vi.fn()} />);
    await userEvent.click(screen.getByTestId('user-menu-toggle'));
    expect(screen.getByText('Appearance')).toBeInTheDocument();
    expect(screen.getByLabelText('light theme')).toBeInTheDocument();
    expect(screen.getByLabelText('dark theme')).toBeInTheDocument();
    expect(screen.getByLabelText('auto theme')).toBeInTheDocument();
  });

  it('shows default sign in text when no REGISTRY_TITLE_SHORT', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {username: ''},
    } as any);
    mockUseQuayConfig.mockReturnValue({
      config: {},
      features: {},
    } as any);
    render(<HeaderToolbar toggleDrawer={vi.fn()} />);
    expect(screen.getByRole('button', {name: /sign in/i})).toBeInTheDocument();
  });
});
