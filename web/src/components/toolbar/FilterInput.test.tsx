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

  it('advanced search panel is present in DOM but hidden before toggle', () => {
    render(<FilterInput searchState={defaultState} onChange={vi.fn()} />);
    const panelById = document.getElementById('filter-input-advanced-search');
    // Panel is always in the DOM — never conditionally unmounted
    expect(panelById).toBeInTheDocument();
    // The panel's wrapper should be hidden initially (display:none via hidden attr)
    expect(panelById!.closest('[hidden]')).toBeInTheDocument();
  });

  it('advanced search panel becomes visible after clicking the toggle button', async () => {
    render(<FilterInput searchState={defaultState} onChange={vi.fn()} />);

    const panelById = document.getElementById('filter-input-advanced-search');
    expect(panelById).toBeInTheDocument();
    // Initially hidden
    expect(panelById!.closest('[hidden]')).toBeInTheDocument();

    // Open the advanced search panel
    await userEvent.click(
      screen.getByRole('button', {name: /open advanced search/i}),
    );

    // Panel should now be visible (wrapper hidden attribute removed)
    expect(panelById!.closest('[hidden]')).toBeNull();
    expect(
      screen.getByRole('checkbox', {name: /use regular expressions/i}),
    ).toBeVisible();
  });

  it('advanced search panel closes after clicking outside', async () => {
    render(
      <div>
        <FilterInput searchState={defaultState} onChange={vi.fn()} />
        <button>outside</button>
      </div>,
    );

    // Open the panel
    await userEvent.click(
      screen.getByRole('button', {name: /open advanced search/i}),
    );

    const panelById = document.getElementById('filter-input-advanced-search');
    expect(panelById!.closest('[hidden]')).toBeNull();

    // Click outside the panel
    await userEvent.click(screen.getByRole('button', {name: /outside/i}));

    expect(panelById!.closest('[hidden]')).toBeInTheDocument();
  });
});
