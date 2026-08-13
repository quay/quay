import {render} from 'src/test-utils';
import {StandaloneMain} from './StandaloneMain';

const mockUseQuayConfigWithLoading = vi.hoisted(() =>
  vi.fn(() => ({
    config: {features: {}, config: {}},
    isLoading: false,
    error: null,
  })),
);

const mockUseCurrentUser = vi.hoisted(() =>
  vi.fn(() => ({
    user: {username: 'testuser', anonymous: false, organizations: []},
    loading: false,
    error: null,
  })),
);

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => mockUseQuayConfigWithLoading().config,
  useQuayConfigWithLoading: mockUseQuayConfigWithLoading,
}));

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: mockUseCurrentUser,
}));

vi.mock('src/hooks/UseExternalScripts', () => ({
  useExternalScripts: vi.fn(),
}));

vi.mock('src/components/header/QuayHeader', () => ({
  QuayHeader: () => <div data-testid="quay-header">Header</div>,
}));

vi.mock('src/components/sidebar/QuaySidebar', () => ({
  QuaySidebar: () => <div>Sidebar</div>,
}));

vi.mock('src/components/footer/QuayFooter', () => ({
  QuayFooter: () => <div>Footer</div>,
}));

vi.mock('src/components/notifications/NotificationDrawerList', () => ({
  NotificationDrawerListComponent: () => <div>Notifications</div>,
}));

vi.mock('src/components/SystemStatusBanner', () => ({
  default: () => null,
}));

vi.mock('src/components/GlobalMessages', () => ({
  GlobalMessages: () => null,
}));

vi.mock('src/components/LoadingPage', () => ({
  LoadingPage: () => <div>Loading...</div>,
}));

vi.mock('src/routes/RegistryStatus', () => ({
  default: () => null,
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useLocation: () => ({pathname: '/', search: '', hash: ''}),
    Navigate: ({to}: {to: string}) => <div data-testid="navigate">{to}</div>,
    Outlet: () => null,
    Routes: ({children}: {children: React.ReactNode}) => <div>{children}</div>,
    Route: () => null,
    useParams: () => ({}),
  };
});

vi.mock('./Alerts', () => ({default: () => null}));

describe('StandaloneMain', () => {
  const originalHref = window.location.href;

  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, 'location', {
      writable: true,
      value: {href: originalHref},
    });
  });

  it('returns null while config is loading', () => {
    mockUseQuayConfigWithLoading.mockReturnValue({
      config: null,
      isLoading: true,
      error: null,
    });
    mockUseCurrentUser.mockReturnValue({
      user: null,
      loading: false,
      error: null,
    });

    const {container} = render(<StandaloneMain />);
    expect(container.innerHTML).toBe('');
  });

  it('returns null while user is loading', () => {
    mockUseQuayConfigWithLoading.mockReturnValue({
      config: {features: {}, config: {}},
      isLoading: false,
      error: null,
    });
    mockUseCurrentUser.mockReturnValue({
      user: null,
      loading: true,
      error: null,
    });

    const {container} = render(<StandaloneMain />);
    expect(container.innerHTML).toBe('');
  });

  it('redirects anonymous user to signin when ANONYMOUS_ACCESS is disabled', () => {
    mockUseQuayConfigWithLoading.mockReturnValue({
      config: {features: {ANONYMOUS_ACCESS: false}, config: {}},
      isLoading: false,
      error: null,
    });
    mockUseCurrentUser.mockReturnValue({
      user: {username: '', anonymous: true, organizations: []},
      loading: false,
      error: null,
    });

    const {container} = render(<StandaloneMain />);
    expect(window.location.href).toBe('/signin');
    expect(container.innerHTML).toBe('');
  });

  it('renders page for anonymous user when ANONYMOUS_ACCESS is enabled', () => {
    mockUseQuayConfigWithLoading.mockReturnValue({
      config: {features: {ANONYMOUS_ACCESS: true}, config: {}},
      isLoading: false,
      error: null,
    });
    mockUseCurrentUser.mockReturnValue({
      user: {username: '', anonymous: true, organizations: []},
      loading: false,
      error: null,
    });

    const {getByTestId} = render(<StandaloneMain />);
    expect(getByTestId('quay-header')).toBeTruthy();
  });

  it('renders page for authenticated user', () => {
    mockUseQuayConfigWithLoading.mockReturnValue({
      config: {features: {}, config: {}},
      isLoading: false,
      error: null,
    });
    mockUseCurrentUser.mockReturnValue({
      user: {username: 'testuser', anonymous: false, organizations: []},
      loading: false,
      error: null,
    });

    const {getByTestId} = render(<StandaloneMain />);
    expect(getByTestId('quay-header')).toBeTruthy();
  });

  it('shows error fallback when config has error', () => {
    mockUseQuayConfigWithLoading.mockReturnValue({
      config: null,
      isLoading: false,
      error: new Error('config failed'),
    });
    mockUseCurrentUser.mockReturnValue({
      user: {username: 'testuser', anonymous: false, organizations: []},
      loading: false,
      error: null,
    });

    const {container} = render(<StandaloneMain />);
    expect(container.textContent).toContain('unavailable');
  });

  it('shows error fallback when user fetch has error', () => {
    mockUseQuayConfigWithLoading.mockReturnValue({
      config: {features: {}, config: {}},
      isLoading: false,
      error: null,
    });
    mockUseCurrentUser.mockReturnValue({
      user: null,
      loading: false,
      error: new Error('user fetch failed'),
    });

    const {container} = render(<StandaloneMain />);
    expect(container.textContent).toContain('unavailable');
  });
});
