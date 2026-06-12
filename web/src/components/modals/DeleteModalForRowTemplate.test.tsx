import {render, screen, userEvent} from 'src/test-utils';
import DeleteModalForRowTemplate from './DeleteModalForRowTemplate';

function makeProps(overrides = {}) {
  return {
    deleteMsgTitle: 'Delete robot account',
    isModalOpen: true,
    toggleModal: vi.fn(),
    deleteHandler: vi.fn(),
    itemToBeDeleted: {name: 'test-robot', description: 'A test robot'},
    keyToDisplay: 'name' as const,
    ...overrides,
  };
}

describe('DeleteModalForRowTemplate', () => {
  it('renders title and item name', () => {
    render(<DeleteModalForRowTemplate {...makeProps()} />);
    expect(screen.getByText('Delete robot account')).toBeInTheDocument();
    expect(screen.getByText('test-robot')).toBeInTheDocument();
  });

  it('calls deleteHandler with item on delete click', async () => {
    const deleteHandler = vi.fn();
    render(<DeleteModalForRowTemplate {...makeProps({deleteHandler})} />);
    await userEvent.click(screen.getByTestId('test-robot-del-btn'));
    expect(deleteHandler).toHaveBeenCalledWith({
      name: 'test-robot',
      description: 'A test robot',
    });
  });

  it('calls toggleModal on cancel click', async () => {
    const toggleModal = vi.fn();
    render(<DeleteModalForRowTemplate {...makeProps({toggleModal})} />);
    await userEvent.click(screen.getByRole('button', {name: /cancel/i}));
    expect(toggleModal).toHaveBeenCalled();
  });
});
