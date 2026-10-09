import {render, screen} from '@testing-library/react';
import RobotTokensModal from './RobotTokensModal';

const configMocks = vi.hoisted(() => ({
  robotAPITokensEnabled: true,
}));

vi.mock('src/components/modals/RobotAPITokensTab', () => ({
  default: () => <div>API tokens</div>,
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

vi.mock('src/hooks/useRobotAccounts', () => ({
  useRobotToken: () => ({regenerateRobotToken: vi.fn()}),
}));

describe('RobotTokensModal', () => {
  beforeEach(() => {
    configMocks.robotAPITokensEnabled = true;
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
});
