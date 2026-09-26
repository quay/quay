import {render, screen} from 'src/test-utils';
import OAuthInformationTab from './OAuthInformationTab';
import type {IOAuthApplication} from 'src/resources/OAuthApplicationTypes';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
);

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

vi.mock('src/hooks/UseOAuthApplications', () => ({
  useResetOAuthApplicationClientSecret: () => ({
    resetClientSecret: vi.fn(),
    isResetting: false,
    error: null,
  }),
}));

const application = {
  name: 'test-app',
  client_id: 'client123',
  client_secret: 'secret456',
  redirect_uri: 'https://example.com/callback',
  application_uri: 'https://example.com',
  avatar_email: '',
  description: 'Test',
} as unknown as IOAuthApplication;

describe('OAuthInformationTab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
  });

  it('enables reset button for non-readonly user', () => {
    render(
      <OAuthInformationTab
        application={application}
        orgName="myorg"
        onSuccess={vi.fn()}
        updateSelectedApplication={vi.fn()}
      />,
    );
    expect(screen.getByTestId('reset-client-secret-button')).not.toBeDisabled();
  });

  it('disables reset button for readonly superuser', () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(
      <OAuthInformationTab
        application={application}
        orgName="myorg"
        onSuccess={vi.fn()}
        updateSelectedApplication={vi.fn()}
      />,
    );
    expect(screen.getByTestId('reset-client-secret-button')).toBeDisabled();
  });
});
