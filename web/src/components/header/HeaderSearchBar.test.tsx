import {render, screen, fireEvent, waitFor} from '@testing-library/react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import {createElement} from 'react';
import HeaderSearchBar from './HeaderSearchBar';

const mockUseSearchSuggestions = vi.hoisted(() => vi.fn());
const mockNavigate = vi.hoisted(() => vi.fn());

vi.mock('src/hooks/UseSearch', () => ({
  useSearchSuggestions: (...args: unknown[]) =>
    mockUseSearchSuggestions(...args),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {...actual, useNavigate: () => mockNavigate};
});

vi.mock('src/components/Avatar', () => ({
  default: () => <span data-testid="avatar" />,
}));

vi.mock('src/libs/avatarUtils', () => ({
  generateAvatarFromName: (name: string) => ({
    name,
    hash: '',
    color: '#000',
    kind: 'generated',
  }),
}));

const repoSuggestion = {
  kind: 'repository',
  title: 'Repo',
  name: 'my-repo',
  namespace: {name: 'myorg', avatar: null},
  href: '/repository/myorg/my-repo',
  score: 5,
};

const orgSuggestion = {
  kind: 'organization',
  title: 'Organization',
  name: 'acme-org',
  avatar: null,
  href: '/organization/acme-org',
  score: 4,
};

function renderSearchBar() {
  const queryClient = new QueryClient({
    defaultOptions: {queries: {retry: false, cacheTime: 0}},
    logger: {log: vi.fn(), warn: vi.fn(), error: vi.fn()},
  });
  return render(
    createElement(
      QueryClientProvider,
      {client: queryClient},
      createElement(MemoryRouter, null, createElement(HeaderSearchBar)),
    ),
  );
}

function getInput() {
  return screen.getByLabelText('Search repositories and organizations');
}

describe('HeaderSearchBar', () => {
  beforeEach(() => {
    mockUseSearchSuggestions.mockReturnValue({
      suggestions: [],
      isLoading: false,
    });
  });

  afterEach(() => vi.clearAllMocks());

  it('renders the search input', () => {
    renderSearchBar();

    expect(getInput()).toBeVisible();
  });

  it('navigates to search page on Enter with no suggestion selected', () => {
    renderSearchBar();

    const input = getInput();
    fireEvent.change(input, {target: {value: 'nginx'}});
    fireEvent.keyDown(input, {key: 'Enter'});

    expect(mockNavigate).toHaveBeenCalledWith('/search?q=nginx');
  });

  it('shows both repository and organization suggestions', async () => {
    mockUseSearchSuggestions.mockReturnValue({
      suggestions: [repoSuggestion, orgSuggestion],
      isLoading: false,
    });

    renderSearchBar();
    fireEvent.change(getInput(), {target: {value: 'myorg'}});

    await waitFor(() => {
      expect(screen.getByText('myorg/my-repo')).toBeVisible();
    });
    expect(screen.getByText('acme-org')).toBeVisible();
  });

  it('navigates to the suggestion href when clicked', async () => {
    mockUseSearchSuggestions.mockReturnValue({
      suggestions: [orgSuggestion],
      isLoading: false,
    });

    renderSearchBar();
    fireEvent.change(getInput(), {target: {value: 'myorg'}});

    await waitFor(() => {
      expect(screen.getByText('acme-org')).toBeVisible();
    });
    fireEvent.click(screen.getByText('acme-org'));

    expect(mockNavigate).toHaveBeenCalledWith('/organization/acme-org');
  });

  it('navigates suggestions with ArrowDown and selects with Enter', async () => {
    mockUseSearchSuggestions.mockReturnValue({
      suggestions: [repoSuggestion, orgSuggestion],
      isLoading: false,
    });

    renderSearchBar();
    const input = getInput();
    fireEvent.change(input, {target: {value: 'myorg'}});

    await waitFor(() => {
      expect(screen.getByText('myorg/my-repo')).toBeVisible();
    });

    fireEvent.keyDown(input, {key: 'ArrowDown'});
    expect(
      screen.getByText('myorg/my-repo').closest('[role="option"]'),
    ).toHaveAttribute('aria-selected', 'true');

    fireEvent.keyDown(input, {key: 'ArrowDown'});
    expect(
      screen.getByText('acme-org').closest('[role="option"]'),
    ).toHaveAttribute('aria-selected', 'true');

    fireEvent.keyDown(input, {key: 'Enter'});
    expect(mockNavigate).toHaveBeenCalledWith('/organization/acme-org');
  });

  it('closes the dropdown on Escape', async () => {
    mockUseSearchSuggestions.mockReturnValue({
      suggestions: [repoSuggestion],
      isLoading: false,
    });

    renderSearchBar();
    const input = getInput();
    fireEvent.change(input, {target: {value: 'myorg'}});

    await waitFor(() => {
      expect(screen.getByText('myorg/my-repo')).toBeVisible();
    });

    fireEvent.keyDown(input, {key: 'Escape'});

    await waitFor(() => {
      expect(screen.queryByText('myorg/my-repo')).not.toBeInTheDocument();
    });
  });

  it('has combobox ARIA attributes on the focusable input itself', () => {
    renderSearchBar();

    // Every combobox attribute must be on the <input> that receives focus.
    // On a wrapper element aria-activedescendant is inert to screen readers.
    const input = screen.getByTestId('header-search-input');
    expect(input.tagName).toBe('INPUT');
    expect(input).toHaveAttribute('role', 'combobox');
    expect(input).toHaveAttribute('aria-expanded', 'false');
    expect(input).toHaveAttribute('aria-controls', 'header-search-suggestions');
    expect(input).toHaveAttribute('aria-autocomplete', 'list');
  });

  it('points aria-activedescendant at the highlighted suggestion', async () => {
    mockUseSearchSuggestions.mockReturnValue({
      suggestions: [repoSuggestion, orgSuggestion],
      isLoading: false,
    });

    renderSearchBar();
    const input = getInput();
    fireEvent.change(input, {target: {value: 'myorg'}});

    await waitFor(() => {
      expect(input).toHaveAttribute('aria-expanded', 'true');
    });
    expect(input).not.toHaveAttribute('aria-activedescendant');

    fireEvent.keyDown(input, {key: 'ArrowDown'});

    expect(input).toHaveAttribute(
      'aria-activedescendant',
      'header-search-suggestion-0',
    );
    expect(
      document.getElementById('header-search-suggestion-0'),
    ).toHaveAttribute('aria-selected', 'true');
  });

  it('keeps the dropdown closed after Escape when suggestions refetch', async () => {
    mockUseSearchSuggestions.mockReturnValue({
      suggestions: [repoSuggestion],
      isLoading: false,
    });

    const {rerender} = renderSearchBar();
    const input = getInput();
    fireEvent.change(input, {target: {value: 'myorg'}});

    await waitFor(() => {
      expect(screen.getByText('myorg/my-repo')).toBeVisible();
    });

    fireEvent.keyDown(input, {key: 'Escape'});
    await waitFor(() => {
      expect(screen.queryByText('myorg/my-repo')).not.toBeInTheDocument();
    });

    // A background refetch returns a new array with identical contents. The
    // dropdown must stay closed rather than reappearing under the user.
    mockUseSearchSuggestions.mockReturnValue({
      suggestions: [{...repoSuggestion}],
      isLoading: false,
    });
    rerender(
      createElement(
        QueryClientProvider,
        {client: new QueryClient({defaultOptions: {queries: {retry: false}}})},
        createElement(MemoryRouter, null, createElement(HeaderSearchBar)),
      ),
    );

    expect(screen.queryByText('myorg/my-repo')).not.toBeInTheDocument();
  });

  it('does not open the dropdown for queries under 3 characters', () => {
    mockUseSearchSuggestions.mockReturnValue({
      suggestions: [repoSuggestion],
      isLoading: false,
    });

    renderSearchBar();
    fireEvent.change(getInput(), {target: {value: 'my'}});

    expect(screen.queryByText('myorg/my-repo')).not.toBeInTheDocument();
  });
});
