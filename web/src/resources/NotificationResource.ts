import {AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {ResourceError, throwIfError} from './ErrorHandling';

export enum NotificationEventType {
  repoPush = 'repo_push',
  vulnFound = 'vulnerability_found',
  buildFailure = 'build_failure',
  buildQueued = 'build_queued',
  buildStart = 'build_start',
  buildSuccess = 'build_success',
  buildCancelled = 'build_cancelled',
  mirrorStarted = 'repo_mirror_sync_started',
  mirrorSuccess = 'repo_mirror_sync_success',
  mirrorFailed = 'repo_mirror_sync_failed',
}

export enum NotificationMethodType {
  email = 'email',
  flowdock = 'flowdock',
  hipchat = 'hipchat',
  quaynotification = 'quay_notification',
  slack = 'slack',
  webhook = 'webhook',
}

export interface RepoNotification {
  config: any;
  event: NotificationEventType;
  event_config: any;
  method: NotificationMethodType;
  title: string;
  number_of_failures?: number;
  uuid?: string;
}

interface FetchNotifiationsResponse {
  notifications: RepoNotification[];
}

export async function fetchNotifications(org: string, repo: string) {
  const url = `/api/v1/repository/${org}/${repo}/notification/`;
  const response: AxiosResponse<FetchNotifiationsResponse> = await axios.get(
    url,
  );
  return response.data.notifications;
}

export async function createNotification(
  org: string,
  repo: string,
  notification: RepoNotification,
) {
  // API requires camal case for this single field, modifying before sending
  // rather than creating a new interface
  const notificationRequest: any = notification;
  notificationRequest.eventConfig = notificationRequest.event_config;
  const url = `/api/v1/repository/${org}/${repo}/notification/`;
  await axios.post(url, notificationRequest);
}

export async function bulkDeleteNotifications(
  org: string,
  repo: string,
  uuids: string[],
) {
  const responses = await Promise.allSettled(
    uuids.map((uuid) => deleteNotification(org, repo, uuid)),
  );
  throwIfError(responses);
}

export async function deleteNotification(
  org: string,
  repo: string,
  uuid: string,
) {
  try {
    const url = `/api/v1/repository/${org}/${repo}/notification/${uuid}`;
    await axios.delete(url);
  } catch (err) {
    throw new ResourceError('failed to delete repository', uuid, err);
  }
}

export async function testNotification(
  org: string,
  repo: string,
  uuid: string,
) {
  const url = `/api/v1/repository/${org}/${repo}/notification/${uuid}/test`;
  await axios.post(url);
}

export async function bulkEnableNotifications(
  org: string,
  repo: string,
  uuids: string[],
) {
  const responses = await Promise.allSettled(
    uuids.map((uuid) => enableNotification(org, repo, uuid)),
  );
  throwIfError(responses);
}

export async function enableNotification(
  org: string,
  repo: string,
  uuid: string,
) {
  try {
    const url = `/api/v1/repository/${org}/${repo}/notification/${uuid}`;
    await axios.post(url);
  } catch (err) {
    throw new ResourceError('failed to enable repository', uuid, err);
  }
}

// TODO: this should be a field from the backend instead of duplicating logic
export function isNotificationDisabled(notification: RepoNotification) {
  return notification.number_of_failures >= 3;
}

export function isNotificationEnabled(notification: RepoNotification) {
  return !isNotificationDisabled(notification);
}
