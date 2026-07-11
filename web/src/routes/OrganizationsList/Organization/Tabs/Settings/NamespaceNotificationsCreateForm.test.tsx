import {render, screen, userEvent, waitFor} from 'src/test-utils';
import NamespaceNotificationsCreateForm from './NamespaceNotificationsCreateForm';

const mockCreate = vi.fn();
const mockResetCreatingNotification = vi.fn();

const mockUseUpdateNamespaceNotifications = vi.hoisted(() =>
  vi.fn(() => ({
    create: mockCreate,
    successCreatingNotification: false,
    isCreatingNotification: false,
    errorCreatingNotification: null,
    resetCreatingNotification: mockResetCreatingNotification,
  })),
);

const mockUseQuayConfig = vi.hoisted(() =>
  vi.fn(() => ({
    features: {MAILING: true, QUOTA_NOTIFICATIONS: true},
    config: {REGISTRY_TITLE_SHORT: 'Quay'},
  })),
);

vi.mock('src/hooks/UseUpdateNamespaceNotifications', () => ({
  useUpdateNamespaceNotifications: mockUseUpdateNamespaceNotifications,
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: mockUseQuayConfig,
}));

vi.mock('src/hooks/UseTeams', () => ({
  useFetchTeams: vi.fn(() => ({teams: []})),
}));

vi.mock('src/hooks/UseOrganizations', () => ({
  useOrganizations: vi.fn(() => ({usernames: ['testuser']})),
}));

vi.mock('src/components/EntitySearch', () => ({
  __esModule: true,
  default: (props: any) => (
    <div data-testid="entity-search">
      <button
        data-testid="select-entity"
        onClick={() =>
          props.onSelect({name: 'testuser', is_robot: false, kind: 'user'})
        }
      >
        Select
      </button>
    </div>
  ),
}));

vi.mock(
  'src/routes/OrganizationsList/Organization/Tabs/DefaultPermissions/createPermissionDrawer/CreateTeamModal',
  () => ({
    CreateTeamModal: () => null,
  }),
);

function renderForm(overrides = {}) {
  const defaultProps = {
    orgname: 'myorg',
    isOpen: true,
    onClose: vi.fn(),
    ...overrides,
  };
  return {
    ...render(<NamespaceNotificationsCreateForm {...defaultProps} />),
    onClose: defaultProps.onClose,
  };
}

describe('NamespaceNotificationsCreateForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseUpdateNamespaceNotifications.mockReturnValue({
      create: mockCreate,
      successCreatingNotification: false,
      isCreatingNotification: false,
      errorCreatingNotification: null,
      resetCreatingNotification: mockResetCreatingNotification,
    });
    mockUseQuayConfig.mockReturnValue({
      features: {MAILING: true, QUOTA_NOTIFICATIONS: true},
      config: {REGISTRY_TITLE_SHORT: 'Quay'},
    });
  });

  it('renders the modal with form fields', () => {
    renderForm();
    expect(screen.getByText('Create notification')).toBeInTheDocument();
    expect(
      screen.getByTestId('ns-notification-event-dropdown'),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId('ns-notification-method-dropdown'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('ns-notification-title')).toBeInTheDocument();
  });

  it('submit button is disabled until form is complete', () => {
    renderForm();
    expect(screen.getByTestId('ns-notification-submit-btn')).toBeDisabled();
  });

  it('selects event from dropdown', async () => {
    renderForm();
    await userEvent.click(
      screen.getByTestId('ns-notification-event-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-event-quota_warning'));
    expect(screen.getByText('Quota Warning')).toBeInTheDocument();
  });

  it('selects email method and enables submit', async () => {
    renderForm();
    await userEvent.click(
      screen.getByTestId('ns-notification-event-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-event-quota_warning'));
    await userEvent.click(
      screen.getByTestId('ns-notification-method-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-method-email'));
    expect(
      screen.getByTestId('ns-notification-submit-btn'),
    ).not.toBeDisabled();
  });

  it('shows email info alert for user namespace', async () => {
    renderForm({isUser: true});
    await userEvent.click(
      screen.getByTestId('ns-notification-event-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-event-quota_warning'));
    await userEvent.click(
      screen.getByTestId('ns-notification-method-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-method-email'));
    expect(
      screen.getByTestId('ns-notification-email-info'),
    ).toBeInTheDocument();
  });

  it('shows slack URL input when slack method selected', async () => {
    renderForm();
    await userEvent.click(
      screen.getByTestId('ns-notification-event-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-event-quota_warning'));
    await userEvent.click(
      screen.getByTestId('ns-notification-method-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-method-slack'));
    expect(
      screen.getByTestId('ns-notification-slack-url'),
    ).toBeInTheDocument();
  });

  it('shows webhook URL and template inputs when webhook method selected', async () => {
    renderForm();
    await userEvent.click(
      screen.getByTestId('ns-notification-event-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-event-quota_warning'));
    await userEvent.click(
      screen.getByTestId('ns-notification-method-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-method-webhook'));
    expect(
      screen.getByTestId('ns-notification-webhook-url'),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId('ns-notification-webhook-template'),
    ).toBeInTheDocument();
  });

  it('shows entity search when quay notification method selected', async () => {
    renderForm();
    await userEvent.click(
      screen.getByTestId('ns-notification-event-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-event-quota_warning'));
    await userEvent.click(
      screen.getByTestId('ns-notification-method-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-method-quay_notification'));
    expect(screen.getByTestId('entity-search')).toBeInTheDocument();
  });

  it('validates slack URL format', async () => {
    renderForm();
    await userEvent.click(
      screen.getByTestId('ns-notification-event-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-event-quota_warning'));
    await userEvent.click(
      screen.getByTestId('ns-notification-method-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-method-slack'));
    await userEvent.type(
      screen.getByTestId('ns-notification-slack-url'),
      'invalid-url',
    );
    expect(
      screen.getByText('Must be a valid Slack webhook URL'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('ns-notification-submit-btn')).toBeDisabled();
  });

  it('validates webhook URL format', async () => {
    renderForm();
    await userEvent.click(
      screen.getByTestId('ns-notification-event-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-event-quota_warning'));
    await userEvent.click(
      screen.getByTestId('ns-notification-method-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-method-webhook'));
    await userEvent.type(
      screen.getByTestId('ns-notification-webhook-url'),
      'not-a-url',
    );
    expect(
      screen.getByText('URL must begin with http(s)://'),
    ).toBeInTheDocument();
  });

  it('submits form with email method', async () => {
    renderForm();
    await userEvent.click(
      screen.getByTestId('ns-notification-event-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-event-quota_warning'));
    await userEvent.click(
      screen.getByTestId('ns-notification-method-dropdown'),
    );
    await userEvent.click(screen.getByTestId('ns-method-email'));
    await userEvent.type(
      screen.getByTestId('ns-notification-title'),
      'Test Title',
    );
    await userEvent.click(screen.getByTestId('ns-notification-submit-btn'));
    expect(mockCreate).toHaveBeenCalledWith({
      config: {},
      event: 'quota_warning',
      event_config: {},
      method: 'email',
      title: 'Test Title',
    });
  });

  it('hides email method when MAILING feature is off', async () => {
    mockUseQuayConfig.mockReturnValue({
      features: {MAILING: false, QUOTA_NOTIFICATIONS: true},
      config: {REGISTRY_TITLE_SHORT: 'Quay'},
    });
    renderForm();
    await userEvent.click(
      screen.getByTestId('ns-notification-method-dropdown'),
    );
    expect(screen.queryByTestId('ns-method-email')).not.toBeInTheDocument();
  });

  it('cancel button calls onClose', async () => {
    const {onClose} = renderForm();
    await userEvent.click(screen.getByRole('button', {name: /cancel/i}));
    expect(onClose).toHaveBeenCalled();
  });
});
