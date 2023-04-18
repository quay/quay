import {useQuery} from '@tanstack/react-query';
import {useState} from 'react';
import {
  fetchNotifications,
  isNotificationDisabled,
  isNotificationEnabled,
  NotificationEventType,
} from 'src/resources/NotificationResource';

export enum NotifiationStatus {
  enabled = 'enabled',
  disabled = 'disabled',
}

export interface NotificationFilter {
  event: NotificationEventType[];
  status: NotifiationStatus[];
}

export function useNotifications(org: string, repo: string) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);
  const [filter, setFilter] = useState<NotificationFilter>({
    event: [],
    status: [],
  });

  const resetFilter = (field = null) => {
    if (field != null) {
      setFilter((prev) => ({...prev, [field]: []}));
    } else {
      setFilter({
        event: [],
        status: [],
      });
    }
  };

  const {
    data: notifications,
    isError: error,
    isLoading: loading,
    isPlaceholderData: isPlaceholderData,
  } = useQuery(
    ['reponotifications', org, repo],
    () => fetchNotifications(org, repo),
    {
      placeholderData: [],
    },
  );

  let filteredNotifications = notifications;
  if (filter.event.length > 0) {
    filteredNotifications = filteredNotifications.filter((n) =>
      filter.event.includes(n.event),
    );
  }
  const showEnabled = filter.status.includes(NotifiationStatus.enabled);
  const showDisabled = filter.status.includes(NotifiationStatus.disabled);
  if (!(showEnabled && showDisabled)) {
    if (showEnabled) {
      filteredNotifications = filteredNotifications.filter((n) =>
        isNotificationEnabled(n),
      );
    }
    if (showDisabled) {
      filteredNotifications = filteredNotifications.filter((n) =>
        isNotificationDisabled(n),
      );
    }
  }

  const paginatedNotifications = filteredNotifications?.slice(
    page * perPage - perPage,
    page * perPage - perPage + perPage,
  );

  return {
    notifications: notifications,
    paginatedNotifications: paginatedNotifications,
    loading: loading || isPlaceholderData,
    error: error,

    page: page,
    setPage: setPage,
    perPage: perPage,
    setPerPage: setPerPage,

    filter: filter,
    setFilter: setFilter,
    resetFilter: resetFilter,
  };
}
