import {render, screen, userEvent} from 'src/test-utils';
import {FilterInput} from './FilterInput';
import {SearchState} from './SearchTypes';

const defaultState: SearchState = {query: '', field: 'Name', isRegEx: false};

describe('FilterInput', () => {
  it('renders the search input with placeholder', () => {
    render(<FilterInput searchState={defaultState} onChange={vi.fn()} />);
    expect(screen.getByPlaceholderText(/search by name/i)).toBeInTheDocument();
  });

  it('calls onChange when user types', async () => {
    const onChange = vi.fn();
    render(<FilterInput searchState={defaultState} onChange={onChange} />);
    await userEvent.type(screen.getByRole('textbox'), 'foo');
    expect(onChange).toHaveBeenCalled();
  });

  it('shows "expression" in placeholder when isRegEx is true', () => {
    render(
      <FilterInput
        searchState={{...defaultState, isRegEx: true}}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByPlaceholderText(/expression/i)).toBeInTheDocument();
  });
});
