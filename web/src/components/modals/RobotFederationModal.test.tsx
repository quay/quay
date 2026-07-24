import {render, screen, userEvent, waitFor} from 'src/test-utils';
import {RobotFederationModal} from './RobotFederationModal';
import {useRobotFederation} from 'src/hooks/useRobotFederation';

vi.mock('src/hooks/useRobotFederation', () => ({
  useRobotFederation: vi.fn(),
}));

const mockUseRobotFederation = vi.mocked(useRobotFederation);

function makeProps(overrides = {}) {
  return {
    robotAccount: {name: 'org+testrobot', token: 'abc'} as any,
    namespace: 'testorg',
    isModalOpen: true,
    setIsModalOpen: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  mockUseRobotFederation.mockReturnValue({
    robotFederationConfig: [],
    loading: false,
    fetchError: null,
    setRobotFederationConfig: vi.fn(),
  } as any);
});

describe('RobotFederationModal', () => {
  it('renders modal with robot name in title', () => {
    render(<RobotFederationModal {...makeProps()} />);
    expect(
      screen.getByText(
        'Robot identity federation configuration for org+testrobot',
      ),
    ).toBeInTheDocument();
  });

  it('shows empty state when no federation configured', () => {
    render(<RobotFederationModal {...makeProps()} />);
    expect(screen.getByText(/No federation configured/)).toBeInTheDocument();
  });

  it('renders existing federation entries', () => {
    mockUseRobotFederation.mockReturnValue({
      robotFederationConfig: [
        {issuer: 'https://issuer.example.com', subject: 'test-subject'},
      ],
      loading: false,
      fetchError: null,
      setRobotFederationConfig: vi.fn(),
    } as any);
    render(<RobotFederationModal {...makeProps()} />);
    expect(
      screen.getByText('https://issuer.example.com : test-subject'),
    ).toBeInTheDocument();
  });
});
