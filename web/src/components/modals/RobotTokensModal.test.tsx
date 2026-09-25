import {render, screen} from '@testing-library/react';
import RobotTokensModal from './RobotTokensModal';

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({config: {SERVER_HOSTNAME: 'quay.example.com'}}),
}));

vi.mock('src/hooks/useRobotAccounts', () => ({
  useRobotToken: () => ({regenerateRobotToken: vi.fn()}),
}));

describe('RobotTokensModal', () => {
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
  });
});
