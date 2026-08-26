import {render, screen, userEvent, waitFor} from 'src/test-utils';
import ChangePasswordModal from './ChangePasswordModal';
import {useUpdateUser} from 'src/hooks/UseCurrentUser';

vi.mock('src/hooks/UseCurrentUser', () => ({
  useUpdateUser: vi.fn(),
}));

const mockUseUpdateUser = vi.mocked(useUpdateUser);

function makeUpdateUser(overrides = {}) {
  return {
    updateUser: vi.fn().mockResolvedValue({}),
    ...overrides,
  };
}

function makeProps(overrides = {}) {
  return {
    isOpen: true,
    onClose: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  mockUseUpdateUser.mockReturnValue(makeUpdateUser());
});

describe('ChangePasswordModal', () => {
  it('renders the modal when isOpen is true', () => {
    render(<ChangePasswordModal {...makeProps()} />);
    expect(screen.getByTestId('change-password-modal')).toBeInTheDocument();
    expect(
      screen.getByText('Passwords must be at least 8 characters long.', {
        exact: false,
      }),
    ).toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    render(<ChangePasswordModal {...makeProps({isOpen: false})} />);
    expect(
      screen.queryByTestId('change-password-modal'),
    ).not.toBeInTheDocument();
  });

  it('shows password-too-short validation error', async () => {
    render(<ChangePasswordModal {...makeProps()} />);
    await userEvent.type(
      screen.getByPlaceholderText('Your new password'),
      'abc',
    );
    expect(
      screen.getByText('Password must be at least 8 characters long'),
    ).toBeInTheDocument();
  });

  it('shows passwords-must-match error when confirm differs', async () => {
    render(<ChangePasswordModal {...makeProps()} />);
    await userEvent.type(
      screen.getByPlaceholderText('Your new password'),
      'password123',
    );
    await userEvent.type(
      screen.getByPlaceholderText('Verify your new password'),
      'different1',
    );
    expect(screen.getByText('Passwords must match')).toBeInTheDocument();
  });

  it('disables submit button when passwords do not match', async () => {
    render(<ChangePasswordModal {...makeProps()} />);
    await userEvent.type(
      screen.getByPlaceholderText('Your new password'),
      'password123',
    );
    await userEvent.type(
      screen.getByPlaceholderText('Verify your new password'),
      'different1',
    );
    expect(screen.getByTestId('change-password-submit')).toBeDisabled();
  });

  it('enables submit button when both passwords match and meet length', async () => {
    render(<ChangePasswordModal {...makeProps()} />);
    await userEvent.type(
      screen.getByPlaceholderText('Your new password'),
      'password123',
    );
    await userEvent.type(
      screen.getByPlaceholderText('Verify your new password'),
      'password123',
    );
    expect(screen.getByTestId('change-password-submit')).not.toBeDisabled();
  });

  it('calls updateUser with the new password on submit', async () => {
    const updateUser = vi.fn().mockResolvedValue({});
    mockUseUpdateUser.mockReturnValue(makeUpdateUser({updateUser}));
    render(<ChangePasswordModal {...makeProps()} />);
    await userEvent.type(
      screen.getByPlaceholderText('Your new password'),
      'password123',
    );
    await userEvent.type(
      screen.getByPlaceholderText('Verify your new password'),
      'password123',
    );
    await userEvent.click(screen.getByTestId('change-password-submit'));
    await waitFor(() =>
      expect(updateUser).toHaveBeenCalledWith({password: 'password123'}),
    );
  });

  it('calls onClose when Cancel is clicked', async () => {
    const onClose = vi.fn();
    render(<ChangePasswordModal {...makeProps({onClose})} />);
    await userEvent.click(screen.getByRole('button', {name: /cancel/i}));
    expect(onClose).toHaveBeenCalled();
  });
});
