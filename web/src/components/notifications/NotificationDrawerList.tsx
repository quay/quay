import {
  Button,
  NotificationDrawerList,
  NotificationDrawerListItem,
  NotificationDrawerListItemHeader,
  NotificationDrawerListItemBody,
  Text,
  TextContent,
} from '@patternfly/react-core';
import {TimesIcon} from '@patternfly/react-icons';
import {useState} from 'react';

import {useAppNotifications} from 'src/hooks/useAppNotifications';
import {getNotificationMessage} from './notificationTemplates';
import {formatDate} from 'src/libs/utils';

export function NotificationDrawerListComponent() {
  const {notifications, dismissNotification, loading} = useAppNotifications();

  const [readNotifications, setReadNotifications] = useState<string[]>(() => {
    const stored = localStorage.getItem('notification-read-status');
    return stored ? JSON.parse(stored) : [];
  });

  const markAsRead = (id: string) => {
    setReadNotifications((prev) => {
      const newRead = [...prev, id];
      localStorage.setItem('notification-read-status', JSON.stringify(newRead));
      return newRead;
    });
  };

  if (loading) return <div>Loading...</div>;

  function mapLevelToVariant(
    level: string,
  ): 'danger' | 'warning' | 'info' | 'success' | 'custom' {
    if (level === 'error') return 'danger';
    if (level === 'primary') return 'info';
    return level as 'danger' | 'warning' | 'info' | 'success' | 'custom';
  }

  function mapButtonVariant(
    kind: string,
  ):
    | 'danger'
    | 'warning'
    | 'primary'
    | 'link'
    | 'secondary'
    | 'tertiary'
    | 'plain'
    | 'control' {
    if (kind === 'default') return 'secondary';
    return kind as
      | 'danger'
      | 'warning'
      | 'primary'
      | 'link'
      | 'secondary'
      | 'tertiary'
      | 'plain'
      | 'control';
  }

  return (
    <NotificationDrawerList>
      {notifications.map((notification) => {
        console.log(notification);
        return (
          <NotificationDrawerListItem
            key={notification.id}
            variant={mapLevelToVariant(notification.level)}
            isRead={readNotifications.includes(notification.id)}
          >
            <NotificationDrawerListItemHeader
              title={getNotificationMessage(notification)}
              variant={mapLevelToVariant(notification.level)}
              onClick={() => markAsRead(notification.id)}
            />
            <NotificationDrawerListItemBody>
              <TextContent>
                <Text component="small" className="pf-v5-u-text-align-right">
                  {formatDate(notification.created, 'medium')}
                </Text>
              </TextContent>
            </NotificationDrawerListItemBody>
            {notification.actions?.map((action, idx) => (
              <Button
                key={idx}
                variant={mapButtonVariant(action.kind)}
                onClick={action.handler}
              >
                {action.title}
              </Button>
            ))}
            <Button
              variant="plain"
              onClick={() => dismissNotification(notification.id)}
              aria-label="Dismiss notification"
            >
              <TimesIcon />
            </Button>
          </NotificationDrawerListItem>
        );
      })}
    </NotificationDrawerList>
  );
}
