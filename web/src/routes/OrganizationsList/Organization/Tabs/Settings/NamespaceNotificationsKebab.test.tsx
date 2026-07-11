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

const mockUseUpdateNamespaceNotifications = vi.hoisted(() =>
  vi.fn(() => ({
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
  })),
);

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

describe('NamespaceNotificationsKebab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseUpdateNamespaceNotifications.mockReturnValue({
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
    });
    mockIsDisabled.mockReturnValue(false);
  });

  it('renders kebab toggle button', () => {
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={enabledNotification}
      />,
    );
    expect(
      screen.getByTestId('uuid-1-ns-toggle-kebab'),
    ).toBeInTheDocument();
  });

  it('shows dropdown menu items on click', async () => {
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={enabledNotification}
      />,
    );
    await userEvent.click(screen.getByTestId('uuid-1-ns-toggle-kebab'));
    expect(
      screen.getByTestId('uuid-1-test-notification'),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId('uuid-1-delete-notification'),
    ).toBeInTheDocument();
  });

  it('calls test mutation when Test Notification is clicked', async () => {
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={enabledNotification}
      />,
    );
    await userEvent.click(screen.getByTestId('uuid-1-ns-toggle-kebab'));
    await userEvent.click(screen.getByTestId('uuid-1-test-notification'));
    expect(mockTest).toHaveBeenCalledWith('uuid-1');
  });

  it('shows delete confirmation modal', async () => {
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={enabledNotification}
      />,
    );
    await userEvent.click(screen.getByTestId('uuid-1-ns-toggle-kebab'));
    await userEvent.click(screen.getByTestId('uuid-1-delete-notification'));
    expect(screen.getByText(/are you sure you want to delete/i)).toBeInTheDocument();
  });

  it('calls deleteNotifications when delete is confirmed', async () => {
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={enabledNotification}
      />,
    );
    await userEvent.click(screen.getByTestId('uuid-1-ns-toggle-kebab'));
    await userEvent.click(screen.getByTestId('uuid-1-delete-notification'));
    await userEvent.click(screen.getByTestId('confirm-delete-ns-notification'));
    expect(mockDeleteNotifications).toHaveBeenCalledWith('uuid-1');
  });

  it('cancel in delete modal does not call delete', async () => {
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={enabledNotification}
      />,
    );
    await userEvent.click(screen.getByTestId('uuid-1-ns-toggle-kebab'));
    await userEvent.click(screen.getByTestId('uuid-1-delete-notification'));
    await userEvent.click(screen.getByRole('button', {name: /cancel/i}));
    expect(mockDeleteNotifications).not.toHaveBeenCalled();
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

  it('calls enableNotifications when Enable is clicked', async () => {
    mockIsDisabled.mockReturnValue(true);
    render(
      <NamespaceNotificationsKebab
        orgname="myorg"
        notification={disabledNotification}
      />,
    );
    await userEvent.click(screen.getByTestId('uuid-2-ns-toggle-kebab'));
    await userEvent.click(screen.getByTestId('uuid-2-enable-notification'));
    expect(mockEnableNotifications).toHaveBeenCalledWith('uuid-2');
  });

  it('shows error alert when delete fails', () => {
    mockUseUpdateNamespaceNotifications.mockReturnValue({
      ...mockUseUpdateNamespaceNotifications(),
      errorDeletingNotification: true,
    });
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
    mockUseUpdateNamespaceNotifications.mockReturnValue({
      ...mockUseUpdateNamespaceNotifications(),
      errorTestingNotification: true,
    });
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
    mockUseUpdateNamespaceNotifications.mockReturnValue({
      ...mockUseUpdateNamespaceNotifications(),
      errorEnablingNotification: true,
    });
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
});
