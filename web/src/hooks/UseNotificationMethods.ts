import {NotificationMethodType} from 'src/resources/NotificationResource';
import {useQuayConfig} from './UseQuayConfig';

export interface NotificationMethod {
  type: NotificationMethodType;
  title: string;
  enabled: boolean;
}

export function useNotificationMethods() {
  const config = useQuayConfig();
  const notificationMethods: NotificationMethod[] = [
    {
      type: NotificationMethodType.email,
      title: 'Email Notification',
      enabled: config?.features.MAILING,
    },
    {
      type: NotificationMethodType.flowdock,
      title: 'Flowdock Team Notification',
      enabled: true,
    },
    {
      type: NotificationMethodType.hipchat,
      title: 'HipChat Room Notification',
      enabled: true,
    },
    {
      type: NotificationMethodType.quaynotification,
      title: `${config?.config.REGISTRY_TITLE_SHORT} Notification`,
      enabled: false, // TODO: Implemented but requires notifications in header to be created
    },
    {
      type: NotificationMethodType.slack,
      title: 'Slack Notification',
      enabled: true,
    },
    {
      type: NotificationMethodType.webhook,
      title: 'Webhook POST',
      enabled: true,
    },
  ];
  return {
    notificationMethods: notificationMethods,
  };
}
