import {renderHook, waitFor, act} from '@testing-library/react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {createElement} from 'react';
import {useSearch, useSearchSuggestions} from './UseSearch';

const mockFetchSearchResults = vi.hoisted(() => vi.fn());
const mockFetchSearchSuggestions = vi.hoisted(() => vi.fn());

vi.mock('src/resources/SearchResource', () => ({
  fetchSearchResults: mockFetchSearchResults,
  fetchSearchSuggestions: mockFetchSearchSuggestions,
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {queries: {retry: false, cacheTime: 0}},
    logger: {log: vi.fn(), warn: vi.fn(), error: vi.fn()},
  });
  function Wrapper({children}: {children: React.ReactNode}) {
    return createElement(QueryClientProvider, {client: queryClient}, children);
  }
  return Wrapper;
}

describe('useSearch', () => {
  afterEach(() => vi.clearAllMocks());

  it('fetches results for a given query and page', async () => {
    mockFetchSearchResults.mockResolvedValue({
      results: [{name: 'repo1', namespace: {name: 'org1'}}],
      has_additional: false,
      page: 1,
      page_size: 10,
      start_index: 0,
    });

    const {result} = renderHook(() => useSearch('test', 1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.results).toHaveLength(1);
    expect(result.current.results[0].name).toBe('repo1');
    expect(result.current.hasAdditional).toBe(false);
    expect(result.current.pageSize).toBe(10);
  });

  it('fetches with empty query', async () => {
    mockFetchSearchResults.mockResolvedValue({
      results: [],
      has_additional: false,
      page: 1,
      page_size: 10,
      start_index: 0,
    });

    const {result} = renderHook(() => useSearch('', 1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(mockFetchSearchResults).toHaveBeenCalledWith('', 1);
  });

  it('returns defaults when data is undefined', () => {
    mockFetchSearchResults.mockReturnValue(new Promise(() => undefined));

    const {result} = renderHook(() => useSearch('test', 1), {
      wrapper: createWrapper(),
    });

    expect(result.current.results).toEqual([]);
    expect(result.current.hasAdditional).toBe(false);
    expect(result.current.pageSize).toBe(10);
    expect(result.current.startIndex).toBe(0);
  });
});

describe('useSearchSuggestions', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('does not fetch when query is shorter than 3 chars', async () => {
    const {result} = renderHook(() => useSearchSuggestions('ab'), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      vi.advanceTimersByTime(300);
    });

    expect(mockFetchSearchSuggestions).not.toHaveBeenCalled();
    expect(result.current.suggestions).toEqual([]);
  });

  it('fetches suggestions after debounce for 3+ char query', async () => {
    vi.useRealTimers();

    mockFetchSearchSuggestions.mockResolvedValue({
      results: [{kind: 'repository', name: 'test-repo'}],
    });

    const {result} = renderHook(() => useSearchSuggestions('test'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.suggestions).toHaveLength(1), {
      timeout: 2000,
    });
    expect(mockFetchSearchSuggestions).toHaveBeenCalledWith('test');
  });
});
