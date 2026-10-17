import {render, screen} from 'src/test-utils';
import SettingsTab from './SettingsTab';
import type {IOAuthApplication} from 'src/resources/OAuthApplicationTypes';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
);

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

vi.mock('src/hooks/UseOAuthApplications', () => ({
  useUpdateOAuthApplication: () => ({
    updateOAuthApplication: vi.fn(),
    isUpdating: false,
    error: null,
  }),
}));

const application = {
  name: 'test-app',
  client_id: 'client1',
  client_secret: 'secret',
  redirect_uri: 'https://example.com/callback',
  application_uri: 'https://example.com',
  avatar_email: '',
  description: 'Test',
} as unknown as IOAuthApplication;

describe('SettingsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
  });

  it('disables update button for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(
      <SettingsTab
        application={application}
        orgName="myorg"
        onSuccess={vi.fn()}
      />,
    );
    expect(screen.getByTestId('update-application-button')).toBeDisabled();
  });

  it('renders update button for non-readonly user', () => {
    render(
      <SettingsTab
        application={application}
        orgName="myorg"
        onSuccess={vi.fn()}
      />,
    );
    expect(screen.getByTestId('update-application-button')).toBeInTheDocument();
  });
});
