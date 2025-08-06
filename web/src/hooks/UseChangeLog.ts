import {useQuery, useQueryClient} from '@tanstack/react-query';
import {fetchChangeLog} from 'src/resources/ChangeLogResource';

interface UseChangeLogWithFreshLogin {
  showFreshLoginModal: (retryOperation: () => Promise<void>) => void;
  isFreshLoginRequired: (error: unknown) => boolean;
}

export function useChangeLog(freshLogin?: UseChangeLogWithFreshLogin) {
  const queryClient = useQueryClient();

  const result = useQuery({
    queryKey: ['changeLog'],
    queryFn: async () => {
      try {
        return await fetchChangeLog();
      } catch (error: unknown) {
        // Check if this is a fresh login required error
        if (freshLogin?.isFreshLoginRequired(error)) {
          // Show fresh login modal with retry operation
          freshLogin.showFreshLoginModal(async () => {
            // Retry the query after successful verification
            queryClient.invalidateQueries({queryKey: ['changeLog']});
          });

          // Don't throw the error - the modal will handle retry
          throw new Error('Fresh login required');
        }
        throw error;
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes - change log doesn't update frequently
    retry: false, // Don't auto-retry, let fresh login handle it
  });

  return {
    ...result,
    changeLog: result.data,
  };
}
