import {useEffect, useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {
  fetchSearchResults,
  fetchSearchSuggestions,
  ISearchResponse,
  ISearchSuggestionsResponse,
} from 'src/resources/SearchResource';

export function useSearchSuggestions(query: string) {
  const [debouncedQuery, setDebouncedQuery] = useState(query);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(query), 250);
    return () => clearTimeout(timer);
  }, [query]);

  const {data, isLoading} = useQuery<ISearchSuggestionsResponse>({
    queryKey: ['searchSuggestions', debouncedQuery],
    queryFn: () => fetchSearchSuggestions(debouncedQuery),
    enabled: debouncedQuery.trim().length >= 3,
    keepPreviousData: true,
  });

  return {
    suggestions: data?.results ?? [],
    isLoading,
  };
}

export function useSearch(query: string, page: number) {
  const {data, isLoading, error} = useQuery<ISearchResponse>({
    queryKey: ['search', query, page],
    queryFn: () => fetchSearchResults(query, page),
    keepPreviousData: true,
  });

  return {
    results: data?.results ?? [],
    hasAdditional: data?.has_additional ?? false,
    page: data?.page ?? page,
    pageSize: data?.page_size ?? 10,
    startIndex: data?.start_index ?? 0,
    isLoading,
    error,
  };
}
