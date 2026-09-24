import {AxiosError, AxiosResponse} from 'axios';
import {ComponentProps} from 'react';
import {NotificationEvent} from 'src/hooks/UseEvents';
import {NotificationMethod} from 'src/hooks/UseNotificationMethods';
import {
  NotificationEventType,
  NotificationMethodType,
} from 'src/resources/NotificationResource';
import {render, screen, userEvent, waitFor} from 'src/test-utils';
import CreateEmailNotification from './NotificationsCreateNotificationEmail';

const event: NotificationEvent = {
  type: NotificationEventType.repoPush,
  title: 'Push to Repository',
  icon: null,
  enabled: true,
};

const method: NotificationMethod = {
  type: NotificationMethodType.email,
  title: 'Email Notification',
  enabled: true,
};

function axiosErrorWithStatus(status: number): AxiosError {
  return new AxiosError(
    'request failed',
    String(status),
    undefined,
    undefined,
    {status} as unknown as AxiosResponse,
  );
}

const mockFetchAuthorizedEmail = vi.hoisted(() => vi.fn());
const mockCreate = vi.hoisted(() => vi.fn());

vi.mock('src/resources/AuthorizedEmailResource', () => ({
  fetchAuthorizedEmail: mockFetchAuthorizedEmail,
  sendAuthorizedEmail: vi.fn(),
}));

vi.mock('src/hooks/UseUpdateNotifications', () => ({
  useUpdateNotifications: () => ({
    create: mockCreate,
    successCreatingNotification: false,
    errorCreatingNotification: null,
    resetCreatingNotification: vi.fn(),
  }),
}));

function renderComponent(
  overrides: Partial<ComponentProps<typeof CreateEmailNotification>> = {},
) {
  const setError = vi.fn();
  const defaultProps: ComponentProps<typeof CreateEmailNotification> = {
    org: 'myorg',
    repo: 'myrepo',
    event,
    method,
    eventConfig: {},
    isValidateConfig: () => true,
    closeDrawer: vi.fn(),
    setError,
    ...overrides,
  };
  render(<CreateEmailNotification {...defaultProps} />);
  return {setError};
}

describe('CreateEmailNotification', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('opens the auth modal without an error when the email has never been authorized (404)', async () => {
    mockFetchAuthorizedEmail.mockRejectedValue(axiosErrorWithStatus(404));
    const {setError} = renderComponent();

    await userEvent.type(
      screen.getByTestId('notification-email'),
      'new@example.com',
    );
    await userEvent.click(screen.getByTestId('notification-submit-btn'));

    await waitFor(() => {
      expect(screen.getByText('Email Authorization')).toBeInTheDocument();
    });
    expect(setError).not.toHaveBeenCalledWith('Unable to verify email');
  });

  it('shows an error and does not open the auth modal on a non-404 failure', async () => {
    mockFetchAuthorizedEmail.mockRejectedValue(axiosErrorWithStatus(500));
    const {setError} = renderComponent();

    await userEvent.type(
      screen.getByTestId('notification-email'),
      'new@example.com',
    );
    await userEvent.click(screen.getByTestId('notification-submit-btn'));

    await waitFor(() => {
      expect(setError).toHaveBeenCalledWith('Unable to verify email');
    });
    expect(screen.queryByText('Email Authorization')).not.toBeInTheDocument();
  });

  it('creates the notification directly when the email is already confirmed', async () => {
    mockFetchAuthorizedEmail.mockResolvedValue({
      email: 'confirmed@example.com',
      repo: 'myrepo',
      namespace: 'myorg',
      confirmed: true,
    });
    const {setError} = renderComponent();

    await userEvent.type(
      screen.getByTestId('notification-email'),
      'confirmed@example.com',
    );
    await userEvent.click(screen.getByTestId('notification-submit-btn'));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalled();
    });
    expect(setError).not.toHaveBeenCalledWith('Unable to verify email');
    expect(screen.queryByText('Email Authorization')).not.toBeInTheDocument();
  });
});
