import {render, screen, userEvent, waitFor} from 'src/test-utils';
import ChangeAccountTypeModal from './ChangeAccountTypeModal';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useConvertAccount} from 'src/hooks/UseConvertAccount';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

vi.mock('src/hooks/UseCurrentUser', () => ({
  useCurrentUser: vi.fn(),
}));

vi.mock('src/hooks/UseConvertAccount', () => ({
  useConvertAccount: vi.fn(),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

vi.mock('src/components/Avatar', () => ({
  default: () => <div data-testid="mock-avatar" />,
}));

const mockUseCurrentUser = vi.mocked(useCurrentUser);
const mockUseConvertAccount = vi.mocked(useConvertAccount);
const mockUseQuayConfig = vi.mocked(useQuayConfig);

function makeProps(overrides = {}) {
  return {
    isOpen: true,
    onClose: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  mockUseCurrentUser.mockReturnValue({
    user: {
      username: 'testuser',
      organizations: [],
      avatar: {name: 'testuser', hash: 'abc', color: '#fff', kind: 'user'},
    },
  } as any);
  mockUseConvertAccount.mockReturnValue({
    convert: vi.fn(),
  } as any);
  mockUseQuayConfig.mockReturnValue({
    features: {BILLING: false},
    config: {},
  } as any);
});

describe('ChangeAccountTypeModal', () => {
  it('renders modal when open', () => {
    render(<ChangeAccountTypeModal {...makeProps()} />);
    expect(screen.getByTestId('change-account-type-modal')).toBeInTheDocument();
    expect(screen.getByText('Change Account Type')).toBeInTheDocument();
  });

  it('shows admin user form when user can convert (no orgs)', () => {
    render(<ChangeAccountTypeModal {...makeProps()} />);
    expect(
      screen.getByText(/Fill out the form below to convert/),
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Admin Username')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Admin Password')).toBeInTheDocument();
  });

  it('shows blocking message when user has organizations', () => {
    mockUseCurrentUser.mockReturnValue({
      user: {
        username: 'testuser',
        organizations: [
          {
            name: 'org1',
            avatar: {name: 'org1', hash: '1', color: '#f00', kind: 'org'},
          },
          {
            name: 'org2',
            avatar: {name: 'org2', hash: '2', color: '#0f0', kind: 'org'},
          },
        ],
        avatar: {name: 'testuser', hash: 'abc', color: '#fff', kind: 'user'},
      },
    } as any);
    render(<ChangeAccountTypeModal {...makeProps()} />);
    expect(
      screen.getByText(/cannot be converted into an organization/),
    ).toBeInTheDocument();
    expect(screen.getByText('org1')).toBeInTheDocument();
    expect(screen.getByText('org2')).toBeInTheDocument();
  });

  it('disables Convert button when admin fields are empty', () => {
    render(<ChangeAccountTypeModal {...makeProps()} />);
    expect(screen.getByTestId('account-type-next')).toBeDisabled();
  });

  it('enables Convert button when admin fields are filled', async () => {
    render(<ChangeAccountTypeModal {...makeProps()} />);
    await userEvent.type(
      screen.getByPlaceholderText('Admin Username'),
      'admin',
    );
    await userEvent.type(
      screen.getByPlaceholderText('Admin Password'),
      'password',
    );
    expect(screen.getByTestId('account-type-next')).not.toBeDisabled();
  });

  it('calls convert on submit when billing is disabled', async () => {
    const convert = vi.fn();
    mockUseConvertAccount.mockReturnValue({convert} as any);
    render(<ChangeAccountTypeModal {...makeProps()} />);
    await userEvent.type(
      screen.getByPlaceholderText('Admin Username'),
      'admin',
    );
    await userEvent.type(
      screen.getByPlaceholderText('Admin Password'),
      'password',
    );
    await userEvent.click(screen.getByTestId('account-type-next'));
    await waitFor(() =>
      expect(convert).toHaveBeenCalledWith({
        adminUser: 'admin',
        adminPassword: 'password',
      }),
    );
  });
});
