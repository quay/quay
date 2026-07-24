import {render, screen} from 'src/test-utils';
import TokenDisplayModal from './TokenDisplayModal';

function makeProps(overrides = {}) {
  return {
    isOpen: true,
    onClose: vi.fn(),
    token: 'test-token-abc123',
    applicationName: 'My Test App',
    scopes: ['repo:read', 'repo:write', 'user:admin'],
    ...overrides,
  };
}

describe('TokenDisplayModal', () => {
  it('renders modal with application name and success alert', () => {
    render(<TokenDisplayModal {...makeProps()} />);
    expect(screen.getByText('Access Token Generated')).toBeInTheDocument();
    expect(screen.getByText(/My Test App/)).toBeInTheDocument();
    expect(
      screen.getByText(/access token has been successfully generated/),
    ).toBeInTheDocument();
  });

  it('displays all scopes', () => {
    render(<TokenDisplayModal {...makeProps()} />);
    expect(screen.getByText('• repo:read')).toBeInTheDocument();
    expect(screen.getByText('• repo:write')).toBeInTheDocument();
    expect(screen.getByText('• user:admin')).toBeInTheDocument();
  });

  it('shows security warning alert', () => {
    render(<TokenDisplayModal {...makeProps()} />);
    expect(screen.getByText('Important Security Notice')).toBeInTheDocument();
    expect(screen.getByText(/Keep this token secure/)).toBeInTheDocument();
  });
});
