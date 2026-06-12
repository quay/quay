import {render, screen, userEvent} from 'src/test-utils';
import DeleteAccountModal from './DeleteAccountModal';

function makeProps(overrides = {}) {
  return {
    isOpen: true,
    onClose: vi.fn(),
    onConfirm: vi.fn(),
    namespaceName: 'testorg',
    namespaceTitle: 'organization',
    ...overrides,
  };
}

describe('DeleteAccountModal', () => {
  it('renders warning and namespace name', () => {
    render(<DeleteAccountModal {...makeProps()} />);
    expect(screen.getByTestId('delete-account-modal')).toBeInTheDocument();
    expect(screen.getByText(/non-reversible/)).toBeInTheDocument();
    expect(screen.getByText('testorg')).toBeInTheDocument();
  });

  it('disables delete button until verification matches', async () => {
    render(<DeleteAccountModal {...makeProps()} />);
    expect(screen.getByTestId('delete-account-confirm')).toBeDisabled();
    await userEvent.type(
      screen.getByPlaceholderText('Enter namespace here'),
      'testorg',
    );
    expect(screen.getByTestId('delete-account-confirm')).not.toBeDisabled();
  });

  it('calls onConfirm when verification matches and delete clicked', async () => {
    const onConfirm = vi.fn();
    render(<DeleteAccountModal {...makeProps({onConfirm})} />);
    await userEvent.type(
      screen.getByPlaceholderText('Enter namespace here'),
      'testorg',
    );
    await userEvent.click(screen.getByTestId('delete-account-confirm'));
    expect(onConfirm).toHaveBeenCalled();
  });

  it('does not call onConfirm when verification does not match', async () => {
    const onConfirm = vi.fn();
    render(<DeleteAccountModal {...makeProps({onConfirm})} />);
    await userEvent.type(
      screen.getByPlaceholderText('Enter namespace here'),
      'wrongname',
    );
    expect(screen.getByTestId('delete-account-confirm')).toBeDisabled();
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
