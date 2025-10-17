import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {
  fetchApplicationTokens,
  createApplicationToken,
  revokeApplicationToken,
  ApplicationTokenError,
  CreateApplicationTokenResponse,
} from 'src/resources/UserResource';
import {AxiosError} from 'axios';

// Hook for fetching application tokens
export function useApplicationTokens() {
  return useQuery(['applicationTokens'], fetchApplicationTokens, {
    staleTime: 30000, // 30 seconds
  });
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
