import {render, screen, userEvent} from 'src/test-utils';
import NamespaceNotificationsKebab from './NamespaceNotificationsKebab';
import {
  NamespaceNotificationEventType,
  NamespaceNotificationMethodType,
} from 'src/resources/NamespaceNotificationResource';

const mockDeleteNotifications = vi.fn();
const mockTest = vi.fn();
const mockEnableNotifications = vi.fn();
const mockResetDeletingNotification = vi.fn();
const mockResetTestingNotification = vi.fn();
const mockResetEnablingNotification = vi.fn();

function defaultHookReturn(overrides: Record<string, unknown> = {}) {
  return {
    deleteNotifications: mockDeleteNotifications,
    errorDeletingNotification: false,
    successDeletingNotification: false,
    resetDeletingNotification: mockResetDeletingNotification,
    test: mockTest,
    errorTestingNotification: false,
    successTestingNotification: false,
    resetTestingNotification: mockResetTestingNotification,
    enableNotifications: mockEnableNotifications,
    errorEnablingNotification: false,
    successEnablingNotification: false,
    resetEnablingNotification: mockResetEnablingNotification,
    ...overrides,
  };
}

const mockUseUpdateNamespaceNotifications = vi.hoisted(() => vi.fn());

const mockIsDisabled = vi.hoisted(() => vi.fn(() => false));

vi.mock('src/hooks/UseUpdateNamespaceNotifications', () => ({
  useUpdateNamespaceNotifications: mockUseUpdateNamespaceNotifications,
}));

vi.mock('src/resources/NamespaceNotificationResource', async () => {
  const actual = await vi.importActual<
    typeof import('src/resources/NamespaceNotificationResource')
  >('src/resources/NamespaceNotificationResource');
  return {
    ...actual,
    isNamespaceNotificationDisabled: mockIsDisabled,
  };
});

const enabledNotification = {
  uuid: 'uuid-1',
  title: 'My Notification',
  event: NamespaceNotificationEventType.quotaWarning,
  method: NamespaceNotificationMethodType.email,
  config: {},
  event_config: {},
  number_of_failures: 0,
};

const disabledNotification = {
  ...enabledNotification,
  uuid: 'uuid-2',
  number_of_failures: 3,
};

const untitledNotification = {
  ...enabledNotification,
  uuid: 'uuid-3',
  title: '',
};

describe('NamespaceNotificationsKebab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseUpdateNamespaceNotifications.mockReturnValue(defaultHookReturn());
    mockIsDisabled.mockReturnValue(false);
  });

  it('renders kebab toggle button', () => {
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={enabledNotification}
      />,
    );
    expect(screen.getByTestId('uuid-1-ns-toggle-kebab')).toBeInTheDocument();
  });

  it('shows dropdown menu items on click', async () => {
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={enabledNotification}
      />,
    );
    await userEvent.click(screen.getByTestId('uuid-1-ns-toggle-kebab'));
    expect(screen.getByTestId('uuid-1-test-notification')).toBeInTheDocument();
    expect(
      screen.getByTestId('uuid-1-delete-notification'),
    ).toBeInTheDocument();
  });

  it('shows Enable option for disabled notifications', async () => {
    mockIsDisabled.mockReturnValue(true);
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={disabledNotification}
      />,
    );
    await userEvent.click(screen.getByTestId('uuid-2-ns-toggle-kebab'));
    expect(
      screen.getByTestId('uuid-2-enable-notification'),
    ).toBeInTheDocument();
  });

  it('does not show Enable option for enabled notifications', async () => {
    mockIsDisabled.mockReturnValue(false);
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={enabledNotification}
      />,
    );
    await userEvent.click(screen.getByTestId('uuid-1-ns-toggle-kebab'));
    expect(
      screen.queryByTestId('uuid-1-enable-notification'),
    ).not.toBeInTheDocument();
  });

  it('shows error alert when delete fails', () => {
    mockUseUpdateNamespaceNotifications.mockReturnValue(
      defaultHookReturn({errorDeletingNotification: true}),
    );
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={enabledNotification}
      />,
    );
    expect(
      screen.getByText(/unable to delete notification/i),
    ).toBeInTheDocument();
  });

  it('shows error alert when test fails', () => {
    mockUseUpdateNamespaceNotifications.mockReturnValue(
      defaultHookReturn({errorTestingNotification: true}),
    );
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={enabledNotification}
      />,
    );
    expect(
      screen.getByText(/unable to test notification/i),
    ).toBeInTheDocument();
  });

  it('shows error alert when enable fails', () => {
    mockUseUpdateNamespaceNotifications.mockReturnValue(
      defaultHookReturn({errorEnablingNotification: true}),
    );
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={enabledNotification}
      />,
    );
    expect(
      screen.getByText(/unable to enable notification/i),
    ).toBeInTheDocument();
  });

  it('shows (Untitled) in error messages for notifications without title', () => {
    mockUseUpdateNamespaceNotifications.mockReturnValue(
      defaultHookReturn({errorDeletingNotification: true}),
    );
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={untitledNotification}
      />,
    );
    expect(
      screen.getByText(/unable to delete notification \(Untitled\)/i),
    ).toBeInTheDocument();
  });

  it('shows test notification queued modal on success', () => {
    mockUseUpdateNamespaceNotifications.mockReturnValue(
      defaultHookReturn({successTestingNotification: true}),
    );
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={enabledNotification}
      />,
    );
    expect(
      screen.getByText(/a test version of this notification has been queued/i),
    ).toBeInTheDocument();
  });
});
