import {render, screen, userEvent} from 'src/test-utils';
import {SearchDropdown} from './SearchDropdown';
import {SearchState} from './SearchTypes';

const defaultState: SearchState = {query: '', field: 'Name'};

describe('SearchDropdown', () => {
  it('renders the current field label', () => {
    render(
      <SearchDropdown
        items={['Name', 'Description']}
        searchState={defaultState}
        setSearchState={vi.fn()}
      />,
    );
    expect(screen.getByText('Name')).toBeInTheDocument();
  });

  it('opens dropdown on toggle click', async () => {
    render(
      <SearchDropdown
        items={['Name', 'Description']}
        searchState={defaultState}
        setSearchState={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole('button', {name: /Name/}));
    expect(screen.getByText('Description')).toBeInTheDocument();
  });

  it('calls setSearchState with selected field', async () => {
    const setSearchState = vi.fn();
    render(
      <SearchDropdown
        items={['Name', 'Description']}
        searchState={defaultState}
        setSearchState={setSearchState}
      />,
    );
    await userEvent.click(screen.getByRole('button', {name: /Name/}));
    await userEvent.click(screen.getByText('Description'));
    expect(setSearchState).toHaveBeenCalled();
  });

  it('logs console error when items is empty', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(vi.fn());
    render(
      <SearchDropdown
        items={[]}
        searchState={defaultState}
        setSearchState={vi.fn()}
      />,
    );
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('No dropdown items'),
    );
    consoleSpy.mockRestore();
  });
});
