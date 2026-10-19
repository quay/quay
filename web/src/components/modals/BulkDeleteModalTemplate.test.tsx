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
});
