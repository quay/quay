import {render, screen, userEvent} from 'src/test-utils';
import {FilterWithDropdown} from './FilterWithDropdown';
import {SearchState} from './SearchTypes';

const defaultState: SearchState = {query: '', field: 'Name'};

describe('FilterWithDropdown', () => {
  it('renders the search text input', () => {
    render(
      <FilterWithDropdown
        searchState={defaultState}
        onChange={vi.fn()}
        dropdownItems={[]}
        searchInputText="Search repos..."
      />,
    );
    expect(screen.getByPlaceholderText('Search repos...')).toBeInTheDocument();
  });

  it('calls onChange as user types', async () => {
    const onChange = vi.fn();
    render(
      <FilterWithDropdown
        searchState={defaultState}
        onChange={onChange}
        dropdownItems={[]}
        searchInputText="Filter..."
      />,
    );
    await userEvent.type(screen.getByPlaceholderText('Filter...'), 'hello');
    expect(onChange).toHaveBeenCalled();
  });

  it('shows clear button when query is non-empty and clears on click', async () => {
    const onChange = vi.fn();
    render(
      <FilterWithDropdown
        searchState={{query: 'some-query', field: 'Name'}}
        onChange={onChange}
        dropdownItems={[]}
        searchInputText="Filter..."
      />,
    );
    const clearBtn = screen.getByRole('button', {name: /clear input/i});
    expect(clearBtn).toBeInTheDocument();
    await userEvent.click(clearBtn);
    expect(onChange).toHaveBeenCalled();
  });
});
