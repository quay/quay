import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import {
  fetchGlobalMessages,
  createGlobalMessage,
  deleteGlobalMessage,
  CreateGlobalMessageRequest,
} from 'src/resources/GlobalMessagesResource';

// Hook for fetching global messages (no auth required)
export function useGlobalMessages() {
  return useQuery({
    queryKey: ['global-messages'],
    queryFn: fetchGlobalMessages,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Hook for creating global messages (requires fresh login)
export function useCreateGlobalMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (messageData: CreateGlobalMessageRequest) => {
      await createGlobalMessage(messageData);
    },
    onSuccess: () => {
      // Invalidate and refetch messages
      queryClient.invalidateQueries({queryKey: ['global-messages']});
    },
  });
}

// Hook for deleting global messages (requires fresh login)
export function useDeleteGlobalMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (uuid: string) => {
      await deleteGlobalMessage(uuid);
    },
    onSuccess: () => {
      // Invalidate and refetch messages
      queryClient.invalidateQueries({queryKey: ['global-messages']});
    },
  });
}
