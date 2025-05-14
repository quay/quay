import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';
import axios from 'src/libs/axios';

export interface AppNotification {
  id: string;
  kind: string;
  message: string;
  level: 'info' | 'warning' | 'error' | 'success';
  read: boolean;
  metadata?: any;
  actions?: Array<{
    title: string;
    kind: 'primary' | 'default';
    handler: () => void;
  }>;
}

function mapAngularLevelToPF(
  level: string,
  metadata?: any,
): 'info' | 'warning' | 'danger' | 'success' {
  if (metadata?.vulnerability?.priority) {
    const priority = metadata.vulnerability.priority;
    if (priority === 'Critical') return 'danger';
    if (priority === 'High' || priority === 'Medium') return 'warning';
    return 'info';
  }

  switch (level) {
    case 'error':
      return 'danger';
    case 'warning':
      return 'warning';
    case 'info':
      return 'info';
    case 'success':
      return 'success';
    default:
      return 'info';
  }
}

export function useAppNotifications() {
  const queryClient = useQueryClient();

  const {data: notifications = [], isLoading: loading} = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => {
      const {data} = await axios.get('/api/v1/user/notifications');
      return data.notifications.map((n: any) => ({
        ...n,
        level: mapAngularLevelToPF(n.level, n.metadata),
      }));
    },
    refetchInterval: 5 * 60 * 1000, // refetch every 5 minutes
  });

  const dismissMutation = useMutation({
    mutationFn: async (id: string) => {
      await axios.put(`/api/v1/user/notifications/${id}`, {dismissed: true});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({queryKey: ['notifications']});
    },
  });

  const unreadCount = notifications.filter((n) => !n.read).length;

  return {
    notifications,
    unreadCount,
    loading,
    dismissNotification: dismissMutation.mutate,
    refetch: () => queryClient.invalidateQueries({queryKey: ['notifications']}),
  };
}
