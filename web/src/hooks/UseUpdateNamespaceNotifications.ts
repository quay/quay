import {useMutation, useQueryClient} from '@tanstack/react-query';
import {
  bulkDeleteNamespaceNotifications,
  bulkEnableNamespaceNotifications,
  createNamespaceNotification,
  NamespaceNotification,
  testNamespaceNotification,
} from 'src/resources/NamespaceNotificationResource';

export function useUpdateNamespaceNotifications(orgname: string) {
  const queryClient = useQueryClient();

  const {
    mutate: create,
    error: errorCreatingNotification,
    isSuccess: successCreatingNotification,
    reset: resetCreatingNotification,
  } = useMutation(
    async (notification: NamespaceNotification) =>
      createNamespaceNotification(orgname, notification),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['namespacenotifications']);
      },
    },
  );

  const {
    mutate: removeNotification,
    isError: errorDeletingNotification,
    isSuccess: successDeletingNotification,
    reset: resetDeletingNotification,
  } = useMutation(
    async (uuids: string | string[]) => {
      uuids = Array.isArray(uuids) ? uuids : [uuids];
      return bulkDeleteNamespaceNotifications(orgname, uuids);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['namespacenotifications']);
      },
    },
  );

  const {
    mutate: test,
    isError: errorTestingNotification,
    isSuccess: successTestingNotification,
    reset: resetTestingNotification,
  } = useMutation(
    async (uuid: string) => testNamespaceNotification(orgname, uuid),
    {
      onSuccess: () => {
        setTimeout(() => {
          queryClient.invalidateQueries({queryKey: ['namespacenotifications']});
        }, 2000);
      },
    },
  );

  const {
    mutate: enable,
    isError: errorEnablingNotification,
    isSuccess: successEnablingNotification,
    reset: resetEnablingNotification,
  } = useMutation(
    async (uuids: string | string[]) => {
      uuids = Array.isArray(uuids) ? uuids : [uuids];
      return bulkEnableNamespaceNotifications(orgname, uuids);
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['namespacenotifications']);
      },
    },
  );

  let errorCreationMessage: string = null;
  if (errorCreatingNotification != null) {
    errorCreationMessage = (errorCreatingNotification as any)?.response?.data
      ?.detail
      ? (errorCreatingNotification as any)?.response?.data?.detail
      : 'Unable to create notification';
  }

  return {
    create,
    successCreatingNotification,
    errorCreatingNotification: errorCreationMessage,
    resetCreatingNotification,

    deleteNotifications: removeNotification,
    errorDeletingNotification,
    successDeletingNotification,
    resetDeletingNotification,

    test,
    errorTestingNotification,
    successTestingNotification,
    resetTestingNotification,

    enableNotifications: enable,
    errorEnablingNotification,
    successEnablingNotification,
    resetEnablingNotification,
  };
}
