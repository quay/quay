import {render, screen} from '@testing-library/react';
import RobotTokensModal from './RobotTokensModal';

const configMocks = vi.hoisted(() => ({
  robotAPITokensEnabled: true,
}));

type MockUser = {
  username: string;
  organizations: Array<{name: string; is_org_admin?: boolean}>;
};

const userMocks = vi.hoisted((): {
  user: MockUser;
  loading: boolean;
  canModifyAsSuperuser: boolean;
} => ({
  user: {
    username: 'example',
    organizations: [],
  },
  loading: false,
  canModifyAsSuperuser: false,
}));

const robotAPITokensTab = vi.hoisted(() => vi.fn(() => <div>API tokens</div>));

vi.mock('src/components/modals/RobotAPITokensTab', () => ({
  default: robotAPITokensTab,
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({
    config: {SERVER_HOSTNAME: 'quay.example.com'},
    features: {ROBOT_API_TOKENS: configMocks.robotAPITokensEnabled},
  }),
}));

vi.mock('src/hooks/UseOrganizations', () => ({
  useOrganizations: () => ({
    usernames: ['example'],
    isSuperUser: false,
    isLoadingSuperUserUsers: false,
  }),
}));

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: () => ({user: userMocks.user, loading: userMocks.loading}),
}));

vi.mock('src/hooks/UseSuperuserPermissions', () => ({
  useSuperuserPermissions: () => ({canModify: userMocks.canModifyAsSuperuser}),
}));

vi.mock('src/hooks/useRobotAccounts', () => ({
  useRobotToken: () => ({regenerateRobotToken: vi.fn()}),
}));

describe('RobotTokensModal', () => {
  beforeEach(() => {
    configMocks.robotAPITokensEnabled = true;
    userMocks.user = {username: 'example', organizations: []};
    userMocks.loading = false;
    userMocks.canModifyAsSuperuser = false;
    robotAPITokensTab.mockClear();
  });

  it('explains that static token rotation does not revoke API tokens', () => {
    render(<RobotTokensModal namespace="example" name="example+builder" />);

    expect(
      screen.getByText(/replaces only this robot's static push\/pull token/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /robot API tokens remain valid and must be revoked separately/i,
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole('tab', {name: /API Tokens/i})).toBeInTheDocument();
  });

  it('hides Robot API Token controls when the feature is disabled', () => {
    configMocks.robotAPITokensEnabled = false;

    render(<RobotTokensModal namespace="example" name="example+builder" />);

    expect(
      screen.queryByRole('tab', {name: /API Tokens/i}),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(/robot API tokens remain valid/i),
    ).not.toBeInTheDocument();
  });

  it('passes management permission only to a namespace manager or full-access superuser', () => {
    userMocks.user = {username: 'readonly', organizations: []};
    render(<RobotTokensModal namespace="otherorg" name="otherorg+builder" />);
    expect(robotAPITokensTab).toHaveBeenLastCalledWith(
      expect.objectContaining({canManageRobotAPITokens: false}),
      undefined,
    );

    userMocks.user = {
      username: 'readonly',
      organizations: [{name: 'otherorg', is_org_admin: true}],
    };
    render(<RobotTokensModal namespace="otherorg" name="otherorg+builder" />);
    expect(robotAPITokensTab).toHaveBeenLastCalledWith(
      expect.objectContaining({canManageRobotAPITokens: true}),
      undefined,
    );

    userMocks.user = {username: 'example', organizations: []};
    render(<RobotTokensModal namespace="example" name="example+builder" />);
    expect(robotAPITokensTab).toHaveBeenLastCalledWith(
      expect.objectContaining({canManageRobotAPITokens: true}),
      undefined,
    );

    userMocks.user = {username: 'superuser', organizations: []};
    userMocks.canModifyAsSuperuser = true;
    render(<RobotTokensModal namespace="otherorg" name="otherorg+builder" />);
    expect(robotAPITokensTab).toHaveBeenLastCalledWith(
      expect.objectContaining({canManageRobotAPITokens: true}),
      undefined,
    );
  });
});
