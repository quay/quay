import {render, screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import TagHistory from './TagHistory';

const mockUseAllTags = vi.hoisted(() => vi.fn());

vi.mock('src/hooks/UseTags', () => ({
  useAllTags: (...args: unknown[]) => mockUseAllTags(...args),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: () => ({registry_state: 'normal', config: {}}),
}));

const mockTag = {
  name: 'latest',
  start_ts: 1000,
  manifest_digest: 'sha256:abc',
  reversion: false,
};

function renderTagHistory() {
  const queryClient = new QueryClient({
    defaultOptions: {queries: {retry: false}},
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TagHistory
        org="myorg"
        repo="myrepo"
        repoDetails={{can_write: false} as any}
      />
    </QueryClientProvider>,
  );
}

describe('TagHistory', () => {
  it('shows the full-page error when the initial load fails', () => {
    mockUseAllTags.mockReturnValue({
      tags: [],
      loadingTags: false,
      errorLoadingTags: true,
      hasMoreTags: false,
      loadMoreTags: vi.fn(),
      loadingMoreTags: false,
    });

    renderTagHistory();

    expect(screen.getByText('Unable to load tag history')).toBeVisible();
    expect(
      screen.queryByRole('grid', {name: 'Tag history table'}),
    ).not.toBeInTheDocument();
  });

  it('keeps loaded rows and shows an inline error when a later page fails', () => {
    mockUseAllTags.mockReturnValue({
      tags: [mockTag],
      loadingTags: false,
      errorLoadingTags: true,
      hasMoreTags: true,
      loadMoreTags: vi.fn(),
      loadingMoreTags: false,
    });

    renderTagHistory();

    expect(screen.getByRole('grid', {name: 'Tag history table'})).toBeVisible();
    expect(screen.getByText('latest')).toBeVisible();
    expect(screen.getByRole('button', {name: 'Load more'})).toBeEnabled();
    expect(screen.getAllByText('Unable to load tag history')).toHaveLength(1);
  });

  it('keeps the search box and shows an inline error when a search fails', async () => {
    mockUseAllTags.mockImplementation(
      (_org: string, _repo: string, query: string) => ({
        tags: [],
        loadingTags: false,
        errorLoadingTags: query !== '',
        hasMoreTags: false,
        loadMoreTags: vi.fn(),
        loadingMoreTags: false,
        debouncedQuery: query,
      }),
    );

    renderTagHistory();

    const search = screen.getByPlaceholderText('Search by tag name...');
    await userEvent.type(search, 'late');

    expect(screen.getByPlaceholderText('Search by tag name...')).toBeVisible();
    expect(screen.getByText('Unable to load tag history')).toBeVisible();
    expect(screen.getByRole('grid', {name: 'Tag history table'})).toBeVisible();
  });
});
