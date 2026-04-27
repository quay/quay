import {render, screen, userEvent} from 'src/test-utils';
import {SearchInput} from './SearchInput';
import {SearchState} from './SearchTypes';

const defaultState: SearchState = {query: '', field: 'Name'};

describe('SearchInput', () => {
  it('renders the search input', () => {
    render(<SearchInput searchState={defaultState} onChange={vi.fn()} />);
    expect(screen.getByRole('searchbox')).toBeInTheDocument();
  });

  it('shows placeholder matching the field name', () => {
    render(<SearchInput searchState={defaultState} onChange={vi.fn()} />);
    expect(
      screen.getByPlaceholderText('Search by Name...'),
    ).toBeInTheDocument();
  });

  it('calls onChange with trimmed query when user types', async () => {
    const onChange = vi.fn();
    render(<SearchInput searchState={defaultState} onChange={onChange} />);
    await userEvent.type(screen.getByRole('searchbox'), 'hello');
    expect(onChange).toHaveBeenCalled();
  });
});
