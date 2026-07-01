import axios from 'src/libs/axios';
import {AxiosResponse} from 'axios';
import {ResourceError, throwIfError} from './ErrorHandling';

export enum NamespaceNotificationEventType {
  quotaWarning = 'quota_warning',
  quotaError = 'quota_error',
}

export enum NamespaceNotificationMethodType {
  email = 'email',
  quaynotification = 'quay_notification',
  slack = 'slack',
  webhook = 'webhook',
}

export interface NamespaceNotification {
  uuid?: string;
  title: string;
  event: NamespaceNotificationEventType;
  method: NamespaceNotificationMethodType;
  config: Record<string, unknown>;
  event_config: Record<string, unknown>;
  number_of_failures?: number;
}

interface FetchNamespaceNotificationsResponse {
  notifications: NamespaceNotification[];
}

export async function fetchNamespaceNotifications(
  orgname: string,
  isUser: boolean = false,
): Promise<NamespaceNotification[]> {
  const url = isUser
    ? '/api/v1/user/notifications'
    : `/api/v1/organization/${orgname}/notifications`;
  const response: AxiosResponse<FetchNamespaceNotificationsResponse> =
    await axios.get(url);
  return response.data.notifications;
}

export async function createNamespaceNotification(
  orgname: string,
  notification: NamespaceNotification,
  isUser: boolean = false,
): Promise<void> {
  const url = isUser
    ? '/api/v1/user/notifications'
    : `/api/v1/organization/${orgname}/notifications`;
  const payload: Record<string, unknown> = {
    event: notification.event,
    method: notification.method,
    config: notification.config,
    eventConfig: notification.event_config,
    title: notification.title,
  };
  await axios.post(url, payload);
}

export async function deleteNamespaceNotification(
  orgname: string,
  uuid: string,
  isUser: boolean = false,
): Promise<void> {
  try {
    const url = isUser
      ? `/api/v1/user/notifications/${uuid}`
      : `/api/v1/organization/${orgname}/notifications/${uuid}`;
    await axios.delete(url);
  } catch (err) {
    throw new ResourceError(
      'failed to delete namespace notification',
      uuid,
      err,
    );
  }
}

export async function bulkDeleteNamespaceNotifications(
  orgname: string,
  uuids: string[],
  isUser: boolean = false,
): Promise<void> {
  const responses = await Promise.allSettled(
    uuids.map((uuid) => deleteNamespaceNotification(orgname, uuid, isUser)),
  );
  throwIfError(responses, 'Unable to delete notifications');
}

export async function testNamespaceNotification(
  orgname: string,
  uuid: string,
  isUser: boolean = false,
): Promise<void> {
  const url = isUser
    ? `/api/v1/user/notifications/${uuid}/test`
    : `/api/v1/organization/${orgname}/notifications/${uuid}/test`;
  await axios.post(url);
}

export async function enableNamespaceNotification(
  orgname: string,
  uuid: string,
  isUser: boolean = false,
): Promise<void> {
  try {
    const url = isUser
      ? `/api/v1/user/notifications/${uuid}`
      : `/api/v1/organization/${orgname}/notifications/${uuid}`;
    await axios.post(url);
  } catch (err) {
    throw new ResourceError(
      'failed to enable namespace notification',
      uuid,
      err,
    );
  }
}

export async function bulkEnableNamespaceNotifications(
  orgname: string,
  uuids: string[],
  isUser: boolean = false,
): Promise<void> {
  const responses = await Promise.allSettled(
    uuids.map((uuid) => enableNamespaceNotification(orgname, uuid, isUser)),
  );
  throwIfError(responses, 'Unable to enable notifications');
}

export function isNamespaceNotificationDisabled(
  notification: NamespaceNotification,
): boolean {
  return notification.number_of_failures >= 3;
}

export function isNamespaceNotificationEnabled(
  notification: NamespaceNotification,
): boolean {
  return !isNamespaceNotificationDisabled(notification);
}
