import {useQuery} from '@tanstack/react-query';
import {useState} from 'react';
import {
  fetchNamespaceNotifications,
  isNamespaceNotificationDisabled,
  isNamespaceNotificationEnabled,
  NamespaceNotificationEventType,
} from 'src/resources/NamespaceNotificationResource';

export enum NamespaceNotificationStatus {
  enabled = 'enabled',
  disabled = 'disabled',
}

export interface NamespaceNotificationFilter {
  event: NamespaceNotificationEventType[];
  status: NamespaceNotificationStatus[];
}

export function useNamespaceNotifications(
  orgname: string,
  isUser: boolean = false,
) {
  const [filter, setFilter] = useState<NamespaceNotificationFilter>({
    event: [],
    status: [],
  });

  const resetFilter = (field: string = null) => {
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
    isPlaceholderData,
  } = useQuery(
    ['namespacenotifications', orgname, isUser],
    () => fetchNamespaceNotifications(orgname, isUser),
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
  const showEnabled = filter.status.includes(
    NamespaceNotificationStatus.enabled,
  );
  const showDisabled = filter.status.includes(
    NamespaceNotificationStatus.disabled,
  );
  if (!(showEnabled && showDisabled)) {
    if (showEnabled) {
      filteredNotifications = filteredNotifications.filter((n) =>
        isNamespaceNotificationEnabled(n),
      );
    }
    if (showDisabled) {
      filteredNotifications = filteredNotifications.filter((n) =>
        isNamespaceNotificationDisabled(n),
      );
    }
  }

  return {
    notifications: filteredNotifications,
    loading: loading || isPlaceholderData,
    error,
    filter,
    setFilter,
    resetFilter,
  };
}
