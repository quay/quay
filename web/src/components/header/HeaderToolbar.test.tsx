import {render, screen, userEvent} from 'src/test-utils';
import {HeaderToolbar} from './HeaderToolbar';

vi.mock('src/contexts/ThemeContext', () => ({
  ThemePreference: {LIGHT: 'LIGHT', DARK: 'DARK', AUTO: 'AUTO'},
  useTheme: vi.fn(() => ({
    themePreference: 'LIGHT',
    setThemePreference: vi.fn(),
  })),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: vi.fn(() => ({user: {username: ''}})),
}));

vi.mock('src/hooks/useAppNotifications', () => ({
  useAppNotifications: vi.fn(() => ({unreadCount: 0})),
}));

vi.mock('src/components/errors/ErrorModal', () => ({
  default: () => null,
}));

vi.mock('react-router-dom', () => ({
  useNavigate: vi.fn(() => vi.fn()),
}));

import {useQuayConfig} from 'src/hooks/UseQuayConfig';

const mockUseQuayConfig = vi.mocked(useQuayConfig);

describe('HeaderToolbar help menu', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows configured documentation and nightly version information', async () => {
    mockUseQuayConfig.mockReturnValue({
      config: {
        DOCUMENTATION_ROOT: 'https://docs.example.test/quay',
        REGISTRY_TITLE_SHORT: 'Quay',
      },
      features: {UI_V2: false},
      version_number: '3.17.9-nightly',
    } as ReturnType<typeof useQuayConfig>);

    render(<HeaderToolbar toggleDrawer={vi.fn()} />);
    await userEvent.click(screen.getByTestId('help-menu-toggle'));

    expect(
      screen.getByRole('menuitem', {name: 'Documentation'}),
    ).toHaveAttribute('href', 'https://docs.example.test/quay');
    expect(
      screen.getByRole('menuitem', {name: 'API Reference'}),
    ).toHaveAttribute('href', '/api/v1/discovery');
    expect(screen.getByTestId('help-version-info')).toHaveTextContent(
      '3.17.9-nightly',
    );

    const apiReference = screen.getByRole('menuitem', {
      name: 'API Reference',
    });
    apiReference.addEventListener('click', (event) => event.preventDefault());
    await userEvent.click(apiReference);
    expect(screen.getByTestId('help-menu-toggle')).toHaveAttribute(
      'aria-expanded',
      'false',
    );
  });

  it('keeps API reference available when documentation and version are absent', async () => {
    mockUseQuayConfig.mockReturnValue({
      config: {REGISTRY_TITLE_SHORT: 'Quay'},
      features: {UI_V2: false},
    } as ReturnType<typeof useQuayConfig>);

    render(<HeaderToolbar toggleDrawer={vi.fn()} />);
    await userEvent.click(screen.getByTestId('help-menu-toggle'));

    expect(screen.getByTestId('help-api-reference-link')).toBeInTheDocument();
    expect(
      screen.queryByTestId('help-documentation-link'),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId('help-version-info')).not.toBeInTheDocument();
  });
});
