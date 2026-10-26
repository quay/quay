import {render, screen, userEvent} from 'src/test-utils';
import NamespaceNotificationsCreateForm from './NamespaceNotificationsCreateForm';

const mockCreate = vi.fn();
const mockResetCreatingNotification = vi.fn();

function defaultHookReturn(overrides: Record<string, unknown> = {}) {
  return {
    create: mockCreate,
    successCreatingNotification: false,
    isCreatingNotification: false,
    errorCreatingNotification: null,
    resetCreatingNotification: mockResetCreatingNotification,
    ...overrides,
  };
}

const mockUseUpdateNamespaceNotifications = vi.hoisted(() => vi.fn());

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
  default: () => <div data-testid="entity-search" />,
}));

vi.mock(
  'src/routes/OrganizationsList/Organization/Tabs/DefaultPermissions/createPermissionDrawer/CreateTeamModal',
  () => ({
    CreateTeamModal: () => null,
  }),
);

function renderForm(overrides: Record<string, unknown> = {}) {
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
    mockUseUpdateNamespaceNotifications.mockReturnValue(defaultHookReturn());
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

  it('shows event options in dropdown', async () => {
    renderForm();
    await userEvent.click(screen.getByTestId('ns-notification-event-dropdown'));
    expect(screen.getByTestId('ns-event-quota_warning')).toBeInTheDocument();
    expect(screen.getByTestId('ns-event-quota_error')).toBeInTheDocument();
  });

  it('selects event from dropdown', async () => {
    renderForm();
    await userEvent.click(screen.getByTestId('ns-notification-event-dropdown'));
    await userEvent.click(screen.getByTestId('ns-event-quota_warning'));
    expect(screen.getByText('Quota Warning')).toBeInTheDocument();
  });

  it('shows method options in dropdown', async () => {
    renderForm();
    await userEvent.click(
      screen.getByTestId('ns-notification-method-dropdown'),
    );
    expect(
      screen.getByTestId('ns-method-quay_notification'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('ns-method-slack')).toBeInTheDocument();
    expect(screen.getByTestId('ns-method-webhook')).toBeInTheDocument();
  });

  it('shows email method when MAILING feature is enabled', async () => {
    renderForm();
    await userEvent.click(
      screen.getByTestId('ns-notification-method-dropdown'),
    );
    expect(screen.getByTestId('ns-method-email')).toBeInTheDocument();
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

  it('submit button remains disabled with only event selected', async () => {
    renderForm();
    await userEvent.click(screen.getByTestId('ns-notification-event-dropdown'));
    await userEvent.click(screen.getByTestId('ns-event-quota_warning'));
    expect(screen.getByTestId('ns-notification-submit-btn')).toBeDisabled();
  });

  it('shows loading state on submit button while creating', () => {
    mockUseUpdateNamespaceNotifications.mockReturnValue(
      defaultHookReturn({isCreatingNotification: true}),
    );
    renderForm();
    expect(screen.getByTestId('ns-notification-submit-btn')).toBeDisabled();
  });

  it('cancel button calls onClose', async () => {
    const {onClose} = renderForm();
    await userEvent.click(screen.getByRole('button', {name: /cancel/i}));
    expect(onClose).toHaveBeenCalled();
  });

  it('does not render modal when isOpen is false', () => {
    renderForm({isOpen: false});
    expect(screen.queryByText('Create notification')).not.toBeInTheDocument();
  });
});
