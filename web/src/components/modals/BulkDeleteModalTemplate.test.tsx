import {fireEvent} from '@testing-library/react';
import {render, screen} from 'src/test-utils';
import {BulkDeleteModalTemplate} from './BulkDeleteModalTemplate';

const items = [{name: 'first'}, {name: 'second'}];
const columns = {Name: {label: 'name'}};

describe('BulkDeleteModalTemplate', () => {
  it('keeps the delete wording when the caller passes none', () => {
    render(
      <BulkDeleteModalTemplate
        mapOfColNamesToTableData={columns}
        isModalOpen={true}
        handleBulkDeletion={vi.fn()}
        selectedItems={items}
        resourceName="robot accounts"
      />,
    );

    expect(
      screen.getByRole('heading', {
        name: /Permanently delete robot accounts\?/,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'This action deletes all robot accounts and cannot be recovered.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Confirm deletion by typing/)).toBeInTheDocument();
    expect(screen.getByTestId('bulk-delete-confirm-btn')).toHaveTextContent(
      'Delete',
    );
  });

  it('uses the wording the caller passes', () => {
    render(
      <BulkDeleteModalTemplate
        mapOfColNamesToTableData={columns}
        isModalOpen={true}
        handleBulkDeletion={vi.fn()}
        selectedItems={items}
        resourceName="robot API tokens"
        title="Revoke 2 robot API tokens?"
        description="Only the selected tokens are revoked."
        confirmationLabel="Confirm revocation by typing"
        actionLabel="Revoke"
      />,
    );

    expect(
      screen.getByRole('heading', {name: /Revoke 2 robot API tokens\?/}),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Only the selected tokens are revoked.'),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Confirm revocation by typing/),
    ).toBeInTheDocument();
    expect(screen.getByTestId('bulk-delete-confirm-btn')).toHaveTextContent(
      'Revoke',
    );
    expect(screen.queryByText(/Permanently delete/)).not.toBeInTheDocument();
  });

  it('resets to page 1 when the search query changes', () => {
    // 21 rows at 20 per page puts item00 on page 1 and item20 on page 2.
    const many = Array.from({length: 21}, (_, i) => ({
      name: `item${String(i).padStart(2, '0')}`,
    }));
    render(
      <BulkDeleteModalTemplate
        mapOfColNamesToTableData={columns}
        isModalOpen={true}
        handleBulkDeletion={vi.fn()}
        selectedItems={many}
        resourceName="robot accounts"
      />,
    );

    fireEvent.click(screen.getAllByLabelText('Go to next page')[0]);
    expect(screen.getByText('item20')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Search'), {
      target: {value: 'item00'},
    });

    expect(screen.getByText('item00')).toBeInTheDocument();
  });
});
