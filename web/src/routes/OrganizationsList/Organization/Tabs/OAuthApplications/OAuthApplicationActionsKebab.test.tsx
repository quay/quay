import {render, screen} from 'src/test-utils';
import OAuthApplicationActionsKebab from './OAuthApplicationActionsKebab';
import type {IOAuthApplication} from 'src/resources/OAuthApplicationTypes';

const mockUseSuperuserPermissions = vi.hoisted(() =>
  vi.fn(() => ({isReadOnlySuperUser: false})),
);

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: mockUseSuperuserPermissions,
}));

vi.mock('src/hooks/UseOAuthApplications', () => ({
  useDeleteOAuthApplication: () => ({
    removeOAuthApplication: vi.fn(),
    errorDeleteOAuthApplication: null,
    successDeleteOAuthApplication: false,
  }),
}));

const application = {
  name: 'test-app',
  client_id: 'client1',
  client_secret: 'secret',
  redirect_uri: 'https://example.com/callback',
  application_uri: 'https://example.com',
  avatar_email: '',
  description: 'Test app',
};

describe('OAuthApplicationActionsKebab', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: false});
  });

  it('shows delete option for non-readonly user', async () => {
    render(
      <OAuthApplicationActionsKebab
        orgName="myorg"
        oauthApplication={application as unknown as IOAuthApplication}
        onEdit={vi.fn()}
      />,
    );
    const toggle = screen.getByTestId('oauth-application-actions');
    await toggle.click();
    expect(
      screen.getByTestId(`${application.name}-del-option`),
    ).toBeInTheDocument();
  });

  it('hides delete option for readonly superuser', async () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(
      <OAuthApplicationActionsKebab
        orgName="myorg"
        oauthApplication={application as unknown as IOAuthApplication}
        onEdit={vi.fn()}
      />,
    );
    const toggle = screen.getByTestId('oauth-application-actions');
    await toggle.click();
    expect(
      screen.queryByTestId(`${application.name}-del-option`),
    ).not.toBeInTheDocument();
  });

  it('always shows edit option regardless of readonly status', async () => {
    mockUseSuperuserPermissions.mockReturnValue({isReadOnlySuperUser: true});
    render(
      <OAuthApplicationActionsKebab
        orgName="myorg"
        oauthApplication={application as unknown as IOAuthApplication}
        onEdit={vi.fn()}
      />,
    );
    const toggle = screen.getByTestId('oauth-application-actions');
    await toggle.click();
    expect(
      screen.getByTestId(`${application.name}-edit-option`),
    ).toBeInTheDocument();
  });
});
