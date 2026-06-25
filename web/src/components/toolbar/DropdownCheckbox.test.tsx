import {render, screen, userEvent} from 'src/test-utils';
import {DropdownCheckbox} from './DropdownCheckbox';

const items = ['alpha', 'beta', 'gamma'];

function makeProps(overrides = {}) {
  return {
    selectedItems: [],
    deSelectAll: vi.fn(),
    allItemsList: items,
    itemsPerPageList: items.slice(0, 2),
    onItemSelect: vi.fn(),
    ...overrides,
  };
}

describe('DropdownCheckbox', () => {
  it('renders the checkbox toggle', () => {
    render(<DropdownCheckbox {...makeProps()} />);
    expect(
      screen.getByRole('checkbox', {name: /select all/i}),
    ).toBeInTheDocument();
  });

  it('shows a badge with count when items are selected', () => {
    render(
      <DropdownCheckbox {...makeProps({selectedItems: ['alpha', 'beta']})} />,
    );
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('calls deSelectAll when unchecking (all items currently selected)', async () => {
    const deSelectAll = vi.fn();
    render(
      <DropdownCheckbox {...makeProps({selectedItems: items, deSelectAll})} />,
    );
    const checkbox = screen.getByRole('checkbox', {name: /select all/i});
    // Checkbox is currently checked (selectedItems.length > 0 => isChecked=true)
    // Clicking unchecks => onChange(false) => deSelectAll()
    await userEvent.click(checkbox);
    expect(deSelectAll).toHaveBeenCalledWith([]);
  });

  it('calls onItemSelect for page items when checking from unchecked state', async () => {
    const onItemSelect = vi.fn();
    const deSelectAll = vi.fn();
    render(
      <DropdownCheckbox
        {...makeProps({selectedItems: [], onItemSelect, deSelectAll})}
      />,
    );
    const checkbox = screen.getByRole('checkbox', {name: /select all/i});
    // Checkbox is unchecked => clicking checks => onChange(true) => selectPageItems()
    await userEvent.click(checkbox);
    expect(deSelectAll).toHaveBeenCalledWith([]);
    expect(onItemSelect).toHaveBeenCalledTimes(2); // itemsPerPageList has 2 items
  });

  it('does not show badge when no items are selected', () => {
    render(<DropdownCheckbox {...makeProps({selectedItems: []})} />);
    // Badge renders selectedItems.length only when > 0; '0' must not appear
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });
});
