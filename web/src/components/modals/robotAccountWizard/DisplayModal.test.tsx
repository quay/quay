import {render, screen, userEvent} from 'src/test-utils';
import DisplayModal from './DisplayModal';

function makeProps(overrides = {}) {
  return {
    isModalOpen: true,
    setIsModalOpen: vi.fn(),
    title: 'Test Modal',
    Component: <div data-testid="modal-content">Content here</div>,
    showSave: false,
    showFooter: true,
    ...overrides,
  };
}

describe('DisplayModal', () => {
  it('renders modal with title and content', () => {
    render(<DisplayModal {...makeProps()} />);
    expect(screen.getByText('Test Modal')).toBeInTheDocument();
    expect(screen.getByTestId('modal-content')).toBeInTheDocument();
  });

  it('shows Close button in footer when showSave is false', () => {
    render(<DisplayModal {...makeProps()} />);
    const closeButtons = screen.getAllByRole('button', {name: /close/i});
    const footerClose = closeButtons.find(
      (btn) => btn.textContent?.trim() === 'Close',
    );
    expect(footerClose).toBeTruthy();
  });

  it('shows Save and Cancel buttons when showSave is true', () => {
    render(<DisplayModal {...makeProps({showSave: true, onSave: vi.fn()})} />);
    expect(screen.getByRole('button', {name: 'Save'})).toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Cancel'})).toBeInTheDocument();
  });

  it('calls setIsModalOpen(false) when footer Close is clicked', async () => {
    const setIsModalOpen = vi.fn();
    render(<DisplayModal {...makeProps({setIsModalOpen})} />);
    const closeButtons = screen.getAllByRole('button', {name: /close/i});
    const footerClose = closeButtons.find(
      (btn) => btn.textContent?.trim() === 'Close',
    );
    expect(footerClose).toBeDefined();
    await userEvent.click(footerClose!);
    expect(setIsModalOpen).toHaveBeenCalledWith(false);
  });

  it('calls onSave when Save button is clicked', async () => {
    const onSave = vi.fn();
    render(
      <DisplayModal
        {...makeProps({showSave: true, onSave, showFooter: true})}
      />,
    );
    await userEvent.click(screen.getByRole('button', {name: 'Save'}));
    expect(onSave).toHaveBeenCalled();
  });
});
