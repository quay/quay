import {render, screen, fireEvent, waitFor} from '@testing-library/react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import {createElement} from 'react';
import Search from './Search';

const mockUseSearch = vi.hoisted(() => vi.fn());
const mockUseSearchSuggestions = vi.hoisted(() => vi.fn());

vi.mock('src/hooks/UseSearch', () => ({
  useSearch: (...args: unknown[]) => mockUseSearch(...args),
  useSearchSuggestions: (...args: unknown[]) =>
    mockUseSearchSuggestions(...args),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({
    config: {SEARCH_MAX_RESULT_PAGE_COUNT: 10},
  }),
}));

vi.mock('src/components/Avatar', () => ({
  default: ({avatar}: {avatar: {name: string}}) => (
    <span data-testid="avatar">{avatar?.name}</span>
  ),
}));

vi.mock('src/libs/avatarUtils', () => ({
  generateAvatarFromName: (name: string) => ({
    name,
    hash: '',
    color: '#000',
    kind: 'generated',
  }),
}));

const defaultSearchReturn = {
  results: [],
  hasAdditional: false,
  page: 1,
  pageSize: 10,
  startIndex: 0,
  isLoading: false,
  error: null,
};

const defaultSuggestionsReturn = {
  suggestions: [],
  isLoading: false,
};

function renderSearch(initialRoute = '/search') {
  const queryClient = new QueryClient({
    defaultOptions: {queries: {retry: false, cacheTime: 0}},
    logger: {log: vi.fn(), warn: vi.fn(), error: vi.fn()},
  });
  return render(
    createElement(
      QueryClientProvider,
      {client: queryClient},
      createElement(
        MemoryRouter,
        {initialEntries: [initialRoute]},
        createElement(Search),
      ),
    ),
  );
}

describe('Search', () => {
  beforeEach(() => {
    mockUseSearch.mockReturnValue(defaultSearchReturn);
    mockUseSearchSuggestions.mockReturnValue(defaultSuggestionsReturn);
  });

  afterEach(() => vi.clearAllMocks());

  it('renders heading and search input', () => {
    renderSearch();

    expect(screen.getByRole('heading', {name: 'Search'})).toBeVisible();
    expect(screen.getByPlaceholderText('Search repositories...')).toBeVisible();
  });

  it('shows "Search for repositories" when no query', () => {
    renderSearch();

    expect(screen.getByText('Search for repositories')).toBeVisible();
    expect(
      screen.getByText('Enter a search term to find repositories.'),
    ).toBeVisible();
  });

  it('shows "No matching repositories found" when query returns no results', () => {
    renderSearch('/search?q=nonexistent');

    expect(screen.getByText('No matching repositories found')).toBeVisible();
    expect(screen.getByText('Please try changing your query.')).toBeVisible();
  });

  it('shows loading spinner', () => {
    mockUseSearch.mockReturnValue({...defaultSearchReturn, isLoading: true});
    renderSearch();

    expect(screen.getByRole('progressbar')).toBeVisible();
  });

  it('shows error state', () => {
    mockUseSearch.mockReturnValue({
      ...defaultSearchReturn,
      error: new Error('fail'),
    });
    renderSearch();

    expect(screen.getByText('Could not load search results')).toBeVisible();
  });

  it('renders search results with repo name and star count', () => {
    mockUseSearch.mockReturnValue({
      ...defaultSearchReturn,
      results: [
        {
          kind: 'repository',
          name: 'my-repo',
          namespace: {
            name: 'myorg',
            avatar: {name: 'myorg', hash: '', color: '#000', kind: 'org'},
          },
          description: 'A test repository',
          href: '/repository/myorg/my-repo',
          stars: 5,
          popularity: 10,
          last_modified: 1700000000,
        },
      ],
    });
    renderSearch();

    expect(screen.getByRole('link', {name: 'myorg/my-repo'})).toBeVisible();
    expect(screen.getByText('5')).toBeVisible();
    expect(screen.getByText('A test repository')).toBeVisible();
  });

  it('shows "Never" for missing last_modified', () => {
    mockUseSearch.mockReturnValue({
      ...defaultSearchReturn,
      results: [
        {
          kind: 'repository',
          name: 'repo1',
          namespace: {name: 'org1', avatar: null},
          href: '/repository/org1/repo1',
          stars: 0,
          popularity: 0,
        },
      ],
    });
    renderSearch();

    expect(screen.getByText(/Never/)).toBeVisible();
  });

  it('submits search on enter key', () => {
    renderSearch();

    const input = screen.getByPlaceholderText('Search repositories...');
    fireEvent.change(input, {target: {value: 'testquery'}});
    fireEvent.keyDown(input, {key: 'Enter'});

    expect(mockUseSearch).toHaveBeenCalledWith('testquery', 1);
  });

  it('clears search on clear button click', () => {
    renderSearch('/search?q=hello');

    const clearButton = screen.getByLabelText('Clear search');
    fireEvent.click(clearButton);

    const input = screen.getByPlaceholderText('Search repositories...');
    expect(input).toHaveValue('');
  });

  it('shows suggestion dropdown', async () => {
    mockUseSearchSuggestions.mockReturnValue({
      suggestions: [
        {
          kind: 'repository',
          title: 'repo',
          name: 'suggest-repo',
          namespace: {name: 'org1', avatar: null},
          href: '/repository/org1/suggest-repo',
          score: 4,
        },
      ],
      isLoading: false,
    });

    renderSearch();

    const input = screen.getByPlaceholderText('Search repositories...');
    fireEvent.change(input, {target: {value: 'suggest'}});

    await waitFor(() => {
      expect(screen.getByRole('menuitem')).toBeVisible();
    });
    expect(screen.getByText('org1/suggest-repo')).toBeVisible();
  });

  it('shows pagination when results have additional pages', () => {
    mockUseSearch.mockReturnValue({
      ...defaultSearchReturn,
      results: [
        {
          kind: 'repository',
          name: 'repo1',
          namespace: {name: 'org1', avatar: null},
          href: '/repository/org1/repo1',
          stars: 0,
          popularity: 0,
        },
      ],
      hasAdditional: true,
    });
    renderSearch();

    expect(screen.getByText(/1 - 1/)).toBeVisible();
  });

  it('shows max results message at page limit', () => {
    mockUseSearch.mockReturnValue({
      ...defaultSearchReturn,
      results: [
        {
          kind: 'repository',
          name: 'repo1',
          namespace: {name: 'org1', avatar: null},
          href: '/repository/org1/repo1',
          stars: 0,
          popularity: 0,
        },
      ],
      page: 10,
    });
    renderSearch('/search?q=test&page=10');

    expect(
      screen.getByText(/maximum number of viewable results/),
    ).toBeVisible();
  });

  it('clamps page to maxPageCount when URL has over-limit page', () => {
    renderSearch('/search?q=test&page=500');

    expect(mockUseSearch).toHaveBeenCalledWith('test', 10);
  });

  it('navigates suggestions with ArrowDown and ArrowUp', async () => {
    mockUseSearchSuggestions.mockReturnValue({
      suggestions: [
        {
          kind: 'repository',
          title: 'repo',
          name: 'repo-a',
          namespace: {name: 'org1', avatar: null},
          href: '/repository/org1/repo-a',
          score: 4,
        },
        {
          kind: 'repository',
          title: 'repo',
          name: 'repo-b',
          namespace: {name: 'org1', avatar: null},
          href: '/repository/org1/repo-b',
          score: 3,
        },
      ],
      isLoading: false,
    });

    renderSearch();

    const input = screen.getByPlaceholderText('Search repositories...');
    fireEvent.change(input, {target: {value: 'repoxyz'}});

    await waitFor(() => {
      expect(screen.getByText('org1/repo-a')).toBeVisible();
    });

    fireEvent.keyDown(input, {key: 'ArrowDown'});
    expect(
      screen.getByText('org1/repo-a').closest('[role="option"]'),
    ).toHaveAttribute('aria-selected', 'true');

    fireEvent.keyDown(input, {key: 'ArrowDown'});
    expect(
      screen.getByText('org1/repo-b').closest('[role="option"]'),
    ).toHaveAttribute('aria-selected', 'true');

    fireEvent.keyDown(input, {key: 'ArrowUp'});
    expect(
      screen.getByText('org1/repo-a').closest('[role="option"]'),
    ).toHaveAttribute('aria-selected', 'true');
  });

  it('has combobox ARIA attributes on search input', () => {
    renderSearch();

    const input = screen.getByPlaceholderText('Search repositories...');
    expect(input).toHaveAttribute('role', 'combobox');
    expect(input).toHaveAttribute(
      'aria-controls',
      'search-suggestions-listbox',
    );

    const wrapper = screen.getByTestId('search-input');
    expect(wrapper).toHaveAttribute('aria-expanded', 'false');
  });
});
