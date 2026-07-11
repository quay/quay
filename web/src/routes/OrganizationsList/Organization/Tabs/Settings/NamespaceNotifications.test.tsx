import {render, screen} from 'src/test-utils';
import NamespaceNotifications from './NamespaceNotifications';
import {
  NamespaceNotificationEventType,
  NamespaceNotificationMethodType,
} from 'src/resources/NamespaceNotificationResource';

const mockUseQuayConfig = vi.hoisted(() =>
  vi.fn(() => ({
    features: {QUOTA_NOTIFICATIONS: true},
    config: {REGISTRY_TITLE_SHORT: 'Quay'},
  })),
);

const mockUseNamespaceNotifications = vi.hoisted(() =>
  vi.fn(() => ({
    notifications: [],
    loading: false,
    error: false,
    filter: {event: [], status: []},
    setFilter: vi.fn(),
    resetFilter: vi.fn(),
  })),
);

const mockIsEnabled = vi.hoisted(() => vi.fn(() => true));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: mockUseQuayConfig,
}));

vi.mock('src/hooks/UseNamespaceNotifications', () => ({
  useNamespaceNotifications: mockUseNamespaceNotifications,
}));

vi.mock('src/resources/NamespaceNotificationResource', async () => {
  const actual = await vi.importActual<
    typeof import('src/resources/NamespaceNotificationResource')
  >('src/resources/NamespaceNotificationResource');
  return {
    ...actual,
    isNamespaceNotificationEnabled: mockIsEnabled,
  };
});

vi.mock('./NamespaceNotificationsCreateForm', () => ({
  default: () => null,
}));

vi.mock('./NamespaceNotificationsKebab', () => ({
  default: () => <div data-testid="kebab-stub" />,
}));

describe('NamespaceNotifications', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseQuayConfig.mockReturnValue({
      features: {QUOTA_NOTIFICATIONS: true},
      config: {REGISTRY_TITLE_SHORT: 'Quay'},
    });
  });

  it('renders spinner while loading', () => {
    mockUseNamespaceNotifications.mockReturnValue({
      notifications: [],
      loading: true,
      error: false,
      filter: {event: [], status: []},
      setFilter: vi.fn(),
      resetFilter: vi.fn(),
    });
    render(<NamespaceNotifications organizationName="myorg" />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders error state', () => {
    mockUseNamespaceNotifications.mockReturnValue({
      notifications: [],
      loading: false,
      error: true,
      filter: {event: [], status: []},
      setFilter: vi.fn(),
      resetFilter: vi.fn(),
    });
    render(<NamespaceNotifications organizationName="myorg" />);
    expect(screen.getByText(/unable to load notifications/i)).toBeInTheDocument();
  });

  it('renders empty state with create button', () => {
    mockUseNamespaceNotifications.mockReturnValue({
      notifications: [],
      loading: false,
      error: false,
      filter: {event: [], status: []},
      setFilter: vi.fn(),
      resetFilter: vi.fn(),
    });
    render(<NamespaceNotifications organizationName="myorg" />);
    expect(
      screen.getByText('No notifications configured'),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId('create-ns-notification-btn'),
    ).toBeInTheDocument();
  });

  it('renders table with notification rows', () => {
    const notifications = [
      {
        uuid: 'n1',
        title: 'My Alert',
        event: NamespaceNotificationEventType.quotaWarning,
        method: NamespaceNotificationMethodType.email,
        config: {},
        event_config: {},
        number_of_failures: 0,
      },
      {
        uuid: 'n2',
        title: '',
        event: NamespaceNotificationEventType.quotaError,
        method: NamespaceNotificationMethodType.slack,
        config: {url: 'https://hooks.slack.com/test'},
        event_config: {},
        number_of_failures: 0,
      },
    ];
    mockUseNamespaceNotifications.mockReturnValue({
      notifications,
      loading: false,
      error: false,
      filter: {event: [], status: []},
      setFilter: vi.fn(),
      resetFilter: vi.fn(),
    });
    render(<NamespaceNotifications organizationName="myorg" />);
    expect(
      screen.getByTestId('ns-notifications-table'),
    ).toBeInTheDocument();
    expect(screen.getByText('My Alert')).toBeInTheDocument();
    expect(screen.getByText('(Untitled)')).toBeInTheDocument();
    expect(screen.getByText('Quota Warning')).toBeInTheDocument();
    expect(screen.getByText('Quota Error')).toBeInTheDocument();
    expect(screen.getByText('Email Notification')).toBeInTheDocument();
    expect(screen.getByText('Slack Notification')).toBeInTheDocument();
  });

  it('displays method titles correctly for all methods', () => {
    const notifications = [
      {
        uuid: 'n1',
        title: 'a',
        event: NamespaceNotificationEventType.quotaWarning,
        method: NamespaceNotificationMethodType.webhook,
        config: {},
        event_config: {},
        number_of_failures: 0,
      },
      {
        uuid: 'n2',
        title: 'b',
        event: NamespaceNotificationEventType.quotaWarning,
        method: NamespaceNotificationMethodType.quaynotification,
        config: {target: {name: 'someuser'}},
        event_config: {},
        number_of_failures: 0,
      },
    ];
    mockUseNamespaceNotifications.mockReturnValue({
      notifications,
      loading: false,
      error: false,
      filter: {event: [], status: []},
      setFilter: vi.fn(),
      resetFilter: vi.fn(),
    });
    render(<NamespaceNotifications organizationName="myorg" />);
    expect(screen.getByText('Webhook POST')).toBeInTheDocument();
    expect(screen.getByText('Quay Notification')).toBeInTheDocument();
  });

  it('displays enabled/disabled status', () => {
    mockIsEnabled.mockImplementation((n: any) => n.uuid === 'n1');
    const notifications = [
      {
        uuid: 'n1',
        title: 'enabled',
        event: NamespaceNotificationEventType.quotaWarning,
        method: NamespaceNotificationMethodType.email,
        config: {},
        event_config: {},
        number_of_failures: 0,
      },
      {
        uuid: 'n2',
        title: 'disabled',
        event: NamespaceNotificationEventType.quotaWarning,
        method: NamespaceNotificationMethodType.email,
        config: {},
        event_config: {},
        number_of_failures: 3,
      },
    ];
    mockUseNamespaceNotifications.mockReturnValue({
      notifications,
      loading: false,
      error: false,
      filter: {event: [], status: []},
      setFilter: vi.fn(),
      resetFilter: vi.fn(),
    });
    render(<NamespaceNotifications organizationName="myorg" />);
    expect(screen.getByText('Enabled')).toBeInTheDocument();
    expect(
      screen.getByText('Disabled (3 failed attempts)'),
    ).toBeInTheDocument();
  });

  it('renders create notification button in table view', () => {
    const notifications = [
      {
        uuid: 'n1',
        title: 'test',
        event: NamespaceNotificationEventType.quotaWarning,
        method: NamespaceNotificationMethodType.email,
        config: {},
        event_config: {},
        number_of_failures: 0,
      },
    ];
    mockUseNamespaceNotifications.mockReturnValue({
      notifications,
      loading: false,
      error: false,
      filter: {event: [], status: []},
      setFilter: vi.fn(),
      resetFilter: vi.fn(),
    });
    render(<NamespaceNotifications organizationName="myorg" />);
    expect(
      screen.getByTestId('create-ns-notification-btn'),
    ).toBeInTheDocument();
  });
});
