import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {
  fetchApplicationTokens,
  fetchApplicationToken,
  createApplicationToken,
  revokeApplicationToken,
  ApplicationTokenError,
  CreateApplicationTokenResponse,
  IApplicationToken,
} from 'src/resources/UserResource';
import {AxiosError} from 'axios';
import {useState} from 'react';
import {SearchState} from 'src/components/toolbar/SearchTypes';

// Hook for fetching application tokens
export function useApplicationTokens() {
  return useQuery(['applicationTokens'], fetchApplicationTokens, {
    staleTime: 30000, // 30 seconds
  });
}

// Hook for fetching application tokens with pagination and filtering
export function useFetchApplicationTokens() {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [search, setSearch] = useState<SearchState>({
    query: '',
    field: 'title',
  });

  const {
    data: tokensData,
    isLoading,
    isError: error,
    isPlaceholderData,
  } = useQuery(['applicationTokens'], fetchApplicationTokens, {
    staleTime: 30000,
    placeholderData: {tokens: []},
  });

  const tokens = tokensData?.tokens || [];

  const filteredTokens =
    search.query !== ''
      ? tokens.filter((token: IApplicationToken) =>
          token.title.toLowerCase().includes(search.query.toLowerCase()),
        )
      : tokens;

  const paginatedTokens = filteredTokens.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  return {
    tokens,
    filteredTokens,
    paginatedTokens,
    isLoading: isLoading || isPlaceholderData,
    error,
    page,
    setPage,
    perPage,
    setPerPage,
    search,
    setSearch,
  };
}

// Hook for creating application tokens
interface UseCreateApplicationTokenProps {
  onSuccess?: (data: CreateApplicationTokenResponse) => void;
  onError?: (error: ApplicationTokenError) => void;
}

export function useCreateApplicationToken({
  onSuccess,
  onError,
}: UseCreateApplicationTokenProps = {}) {
  const queryClient = useQueryClient();

  return useMutation(
    async (title: string) => {
      return createApplicationToken(title);
    },
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries(['applicationTokens']);
        onSuccess?.(data);
      },
      onError: (err: AxiosError) => {
        const error = new ApplicationTokenError(
          'Failed to create application token',
          '',
          err,
        );
        onError?.(error);
      },
    },
  );
}

// Hook for fetching a specific application token
export function useApplicationToken(tokenUuid: string | null) {
  return useQuery(
    ['applicationToken', tokenUuid],
    () => fetchApplicationToken(tokenUuid as string),
    {
      enabled: !!tokenUuid,
      staleTime: 0, // Always fetch fresh data for security
    },
  );
}

// Hook for revoking application tokens
interface UseRevokeApplicationTokenProps {
  onSuccess?: () => void;
  onError?: (error: ApplicationTokenError) => void;
}

export function useRevokeApplicationToken({
  onSuccess,
  onError,
}: UseRevokeApplicationTokenProps = {}) {
  const queryClient = useQueryClient();

  return useMutation(
    async (tokenUuid: string) => {
      return revokeApplicationToken(tokenUuid);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['applicationTokens']);
        onSuccess?.();
      },
      onError: (err: AxiosError) => {
        const error = new ApplicationTokenError(
          'Failed to revoke application token',
          '',
          err,
        );
        onError?.(error);
      },
    },
  );
}
