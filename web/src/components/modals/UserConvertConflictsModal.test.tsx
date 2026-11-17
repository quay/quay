import {fireEvent} from '@testing-library/react';
import {render, screen} from 'src/test-utils';
import {UserConvertConflictsModal} from './UserConvertConflictsModal';

describe('UserConvertConflictsModal', () => {
  it('resets to page 1 when the search query changes', () => {
    // 11 rows at 10 per page puts item00 on page 1 and item10 on page 2.
    const items = Array.from({length: 11}, (_, i) => ({
      name: `item${String(i).padStart(2, '0')}`,
      is_org_admin: false,
    }));
    render(
      <UserConvertConflictsModal
        mapOfColNamesToTableData={{}}
        isModalOpen={true}
        items={items as never}
      />,
    );

    fireEvent.click(screen.getAllByLabelText('Go to next page')[0]);
    expect(screen.getByText('item10')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('Search'), {
      target: {value: 'item00'},
    });

    expect(screen.getByText('item00')).toBeInTheDocument();
  });
});
