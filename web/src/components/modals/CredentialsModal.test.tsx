import {render, screen, userEvent} from 'src/test-utils';
import CredentialsModal from './CredentialsModal';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

const mockUseQuayConfig = vi.mocked(useQuayConfig);

const testCredentials = {
  username: 'testuser',
  password: 'secret-token-123',
  title: 'MyApp',
};

function makeProps(overrides = {}) {
  return {
    isOpen: true,
    onClose: vi.fn(),
    credentials: testCredentials,
    type: 'token' as const,
    ...overrides,
  };
}

beforeEach(() => {
  mockUseQuayConfig.mockReturnValue({
    config: {SERVER_HOSTNAME: 'quay.example.com'},
    features: {},
  } as any);
});

describe('CredentialsModal', () => {
  it('renders modal with credentials title', () => {
    render(<CredentialsModal {...makeProps()} />);
    expect(screen.getByTestId('credentials-modal')).toBeInTheDocument();
    expect(screen.getByText('Credentials for MyApp')).toBeInTheDocument();
  });

  it('shows Application Token tab for token type', () => {
    render(<CredentialsModal {...makeProps()} />);
    expect(
      screen.getByRole('tab', {name: /Application Token/}),
    ).toBeInTheDocument();
  });

  it('shows Encrypted Password tab for encrypted-password type', () => {
    render(<CredentialsModal {...makeProps({type: 'encrypted-password'})} />);
    expect(
      screen.getByRole('tab', {name: /Encrypted Password/}),
    ).toBeInTheDocument();
  });

  it('displays username and password via clipboard copy', () => {
    render(<CredentialsModal {...makeProps()} />);
    const usernameEl = screen.getByTestId('credentials-modal-copy-username');
    const passwordEl = screen.getByTestId('credentials-modal-copy-password');
    expect(
      usernameEl.querySelector('input') ?? usernameEl.querySelector('pre'),
    ).toBeTruthy();
    expect(passwordEl).toBeInTheDocument();
  });

  it('shows newly created alert for new tokens', () => {
    render(<CredentialsModal {...makeProps({isNewlyCreated: true})} />);
    expect(screen.getByText('Token Created Successfully')).toBeInTheDocument();
  });

  it('renders all six tabs', () => {
    render(<CredentialsModal {...makeProps()} />);
    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(6);
    expect(tabs[0]).toHaveTextContent('Application Token');
    expect(tabs[1]).toHaveTextContent('Kubernetes Secret');
    expect(tabs[2]).toHaveTextContent('rkt Configuration');
    expect(tabs[3]).toHaveTextContent('Podman Login');
    expect(tabs[4]).toHaveTextContent('Docker Login');
    expect(tabs[5]).toHaveTextContent('Docker Configuration');
  });

  it('shows podman login command on Podman tab', async () => {
    render(<CredentialsModal {...makeProps()} />);
    await userEvent.click(screen.getByRole('tab', {name: /Podman Login/}));
    expect(screen.getByText('Run podman login command')).toBeInTheDocument();
  });

  it('calls onClose when Done is clicked', async () => {
    const onClose = vi.fn();
    render(<CredentialsModal {...makeProps({onClose})} />);
    await userEvent.click(screen.getByTestId('credentials-modal-close'));
    expect(onClose).toHaveBeenCalled();
  });
});
