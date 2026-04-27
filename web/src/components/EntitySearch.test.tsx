import {render, screen, userEvent, waitFor} from 'src/test-utils';
import EntitySearch from './EntitySearch';
import {useEntities} from 'src/hooks/UseEntities';

vi.mock('src/hooks/UseEntities', () => ({
  useEntities: vi.fn(),
}));

const mockUseEntities = vi.mocked(useEntities);

function defaultHookReturn(overrides = {}) {
  return {
    entities: [],
    isError: false,
    searchTerm: '',
    setSearchTerm: vi.fn(),
    setEntities: vi.fn(),
    ...overrides,
  };
}

function makeProps(overrides = {}) {
  return {
    org: 'myorg',
    onSelect: vi.fn(),
    onClear: vi.fn(),
    onError: vi.fn(),
    placeholderText: 'Search users',
    ...overrides,
  };
}

beforeEach(() => {
  mockUseEntities.mockReturnValue(defaultHookReturn());
});

describe('EntitySearch', () => {
  it('renders the search input with placeholder', () => {
    render(<EntitySearch {...makeProps()} />);
    expect(screen.getByPlaceholderText('Search users')).toBeInTheDocument();
  });

  it('calls setSearchTerm as user types', async () => {
    const setSearchTerm = vi.fn();
    mockUseEntities.mockReturnValue(defaultHookReturn({setSearchTerm}));
    render(<EntitySearch {...makeProps()} />);
    await userEvent.type(screen.getByPlaceholderText('Search users'), 'alice');
    expect(setSearchTerm).toHaveBeenCalled();
  });

  it('shows entity options when entities are returned', async () => {
    mockUseEntities.mockReturnValue(
      defaultHookReturn({
        searchTerm: 'ali',
        entities: [
          {name: 'alice', kind: 'user'},
          {name: 'alice-robot', kind: 'robot'},
        ],
      }),
    );
    render(<EntitySearch {...makeProps()} />);
    // Click the combobox input to open the dropdown
    await userEvent.click(screen.getByRole('combobox'));
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('alice-robot')).toBeInTheDocument();
  });

  it('shows "No results found" when entities is empty and search is active', async () => {
    mockUseEntities.mockReturnValue(
      defaultHookReturn({searchTerm: 'zzz', entities: []}),
    );
    render(<EntitySearch {...makeProps()} />);
    await userEvent.click(screen.getByRole('combobox'));
    expect(screen.getByText('No results found')).toBeInTheDocument();
  });

  it('shows clear button when searchTerm is non-empty', () => {
    mockUseEntities.mockReturnValue(defaultHookReturn({searchTerm: 'bob'}));
    render(<EntitySearch {...makeProps()} />);
    expect(
      screen.getByRole('button', {name: /clear input value/i}),
    ).toBeInTheDocument();
  });

  it('calls onError when isError is true', async () => {
    const onError = vi.fn();
    mockUseEntities.mockReturnValue(defaultHookReturn({isError: true}));
    render(<EntitySearch {...makeProps({onError})} />);
    await waitFor(() => expect(onError).toHaveBeenCalled());
  });

  it('shows "not permitted" message when robots and teams are both excluded', async () => {
    mockUseEntities.mockReturnValue(
      defaultHookReturn({searchTerm: 'test', entities: []}),
    );
    render(
      <EntitySearch
        {...makeProps({includeRobots: false, includeTeams: false})}
      />,
    );
    await userEvent.click(screen.getByRole('combobox'));
    expect(
      screen.getByText('Robot accounts and teams are not permitted'),
    ).toBeInTheDocument();
  });

  it('passes includeTeams and includeRobots to useEntities', () => {
    render(
      <EntitySearch
        {...makeProps({includeTeams: false, includeRobots: true})}
      />,
    );
    expect(mockUseEntities).toHaveBeenCalledWith('myorg', false, true);
  });
});
