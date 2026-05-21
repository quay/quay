import {render, screen, userEvent, waitFor} from 'src/test-utils';
import {BulkDeleteModalTemplate} from './BulkDeleteModalTemplate';

const selectedItems = [
  {name: 'robot1', description: 'First robot'},
  {name: 'robot2', description: 'Second robot'},
  {name: 'robot3', description: 'Third robot'},
];

function makeProps(overrides = {}) {
  return {
    mapOfColNamesToTableData: {
      Name: {label: 'name'},
      Description: {label: 'description'},
    },
    isModalOpen: true,
    handleModalToggle: vi.fn(),
    handleBulkDeletion: vi.fn(),
    selectedItems,
    resourceName: 'robot accounts',
    ...overrides,
  };
}

describe('BulkDeleteModalTemplate', () => {
  it('renders modal with items and confirmation input', () => {
    render(<BulkDeleteModalTemplate {...makeProps()} />);
    expect(screen.getByTestId('bulk-delete-modal')).toBeInTheDocument();
    expect(
      screen.getByText('Permanently delete robot accounts?'),
    ).toBeInTheDocument();
    expect(screen.getByText('robot1')).toBeInTheDocument();
    expect(screen.getByText('robot2')).toBeInTheDocument();
  });

  it('disables delete button until "confirm" is typed', async () => {
    render(<BulkDeleteModalTemplate {...makeProps()} />);
    expect(screen.getByTestId('bulk-delete-confirm-btn')).toBeDisabled();
    await userEvent.type(
      screen.getByTestId('delete-confirmation-input'),
      'confirm',
    );
    expect(screen.getByTestId('bulk-delete-confirm-btn')).not.toBeDisabled();
  });

  it('calls handleBulkDeletion on confirm', async () => {
    const handleBulkDeletion = vi.fn();
    render(<BulkDeleteModalTemplate {...makeProps({handleBulkDeletion})} />);
    await userEvent.type(
      screen.getByTestId('delete-confirmation-input'),
      'confirm',
    );
    await userEvent.click(screen.getByTestId('bulk-delete-confirm-btn'));
    await waitFor(() =>
      expect(handleBulkDeletion).toHaveBeenCalledWith(selectedItems),
    );
  });

  it('filters items by search input', async () => {
    render(<BulkDeleteModalTemplate {...makeProps()} />);
    const searchInput = screen.getByPlaceholderText('Search');
    await userEvent.type(searchInput, 'robot1');
    expect(screen.getByText('robot1')).toBeInTheDocument();
    expect(screen.queryByText('robot2')).not.toBeInTheDocument();
  });
});
