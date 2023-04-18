import {useMutation, useQueryClient} from '@tanstack/react-query';
import {
  bulkDeleteNotifications,
  bulkEnableNotifications,
  createNotification,
  testNotification,
} from 'src/resources/NotificationResource';
import {RepoNotification} from 'src/resources/NotificationResource';

export function useUpdateNotifications(org: string, repo: string) {
  const queryClient = useQueryClient();
  const {
    mutate: create,
    error: errorCreatingNotification,
    isSuccess: successCreatingNotification,
    reset: resetCreatingNotification,
  } = useMutation(
    async (notification: RepoNotification) =>
      createNotification(org, repo, notification),
    {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries(['reponotifications']);
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
      return bulkDeleteNotifications(org, repo, uuids);
    },
    {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries(['reponotifications']);
      },
    },
  );

  const {
    mutate: test,
    isError: errorTestingNotification,
    isSuccess: successTestingNotification,
    reset: resetTestingNotification,
  } = useMutation(async (uuid: string) => testNotification(org, repo, uuid));

  const {
    mutate: enable,
    isError: errorEnablingNotification,
    isSuccess: successEnablingNotification,
    reset: resetEnablingNotification,
  } = useMutation(
    async (uuids: string | string[]) => {
      uuids = Array.isArray(uuids) ? uuids : [uuids];
      return bulkEnableNotifications(org, repo, uuids);
    },
    {
      onSuccess: (_, variables) => {
        queryClient.invalidateQueries(['reponotifications']);
      },
    },
  );
  let errorCreationMessage = null;
  if (errorCreatingNotification != null) {
    errorCreationMessage = (errorCreatingNotification as any)?.response?.data
      ?.detail
      ? (errorCreatingNotification as any)?.response?.data?.detail
      : 'Unable to create notification';
  }

  return {
    create: create,
    successCreatingNotification: successCreatingNotification,
    errorCreatingNotification: errorCreationMessage,
    resetCreatingNotification: resetCreatingNotification,

    deleteNotifications: removeNotification,
    errorDeletingNotification: errorDeletingNotification,
    successDeletingNotification: successDeletingNotification,
    resetDeletingNotification: resetDeletingNotification,

    test: test,
    errorTestingNotification: errorTestingNotification,
    successTestingNotification: successTestingNotification,
    resetTestingNotification: resetTestingNotification,

    enableNotifications: enable,
    errorEnablingNotification: errorEnablingNotification,
    successEnablingNotification: successEnablingNotification,
    resetEnablingNotification: resetEnablingNotification,
  };
}
