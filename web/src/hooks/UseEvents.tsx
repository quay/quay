import {
  BugIcon,
  CheckCircleIcon,
  MinusCircleIcon,
  SyncAltIcon,
  TaskIcon,
  TimesCircleIcon,
  UploadIcon,
} from '@patternfly/react-icons';
import {NotificationEventType} from 'src/resources/NotificationResource';
import {useQuayConfig} from './UseQuayConfig';

export interface NotificationEvent {
  type: NotificationEventType;
  title: string;
  icon: React.ReactNode;
  enabled: boolean;
}

export function useEvents() {
  const config = useQuayConfig();
  const events: NotificationEvent[] = [
    {
      type: NotificationEventType.repoPush,
      title: 'Push to Repository',
      icon: <UploadIcon />,
      enabled: true,
    },
    {
      type: NotificationEventType.vulnFound,
      title: 'Package Vulnerability Found',
      icon: <BugIcon />,
      enabled: config?.features.SECURITY_SCANNER,
    },
    {
      type: NotificationEventType.buildFailure,
      title: 'Image build failed',
      icon: <TimesCircleIcon />,
      enabled: config?.features.BUILD_SUPPORT,
    },
    {
      type: NotificationEventType.buildQueued,
      title: 'Image build queued',
      icon: <TaskIcon />,
      enabled: config?.features.BUILD_SUPPORT,
    },
    {
      type: NotificationEventType.buildStart,
      title: 'Image build started',
      icon: <SyncAltIcon />,
      enabled: config?.features.BUILD_SUPPORT,
    },
    {
      type: NotificationEventType.buildSuccess,
      title: 'Image build success',
      icon: <CheckCircleIcon />,
      enabled: config?.features.BUILD_SUPPORT,
    },
    {
      type: NotificationEventType.buildCancelled,
      title: 'Image build cancelled',
      icon: <MinusCircleIcon />,
      enabled: config?.features.BUILD_SUPPORT,
    },
    {
      type: NotificationEventType.mirrorStarted,
      title: 'Repository mirror started',
      icon: <SyncAltIcon />,
      enabled: config?.features.REPO_MIRROR,
    },
    {
      type: NotificationEventType.mirrorSuccess,
      title: 'Repository mirror successful',
      icon: <CheckCircleIcon />,
      enabled: config?.features.REPO_MIRROR,
    },
    {
      type: NotificationEventType.mirrorFailed,
      title: 'Repository mirror unsuccessful',
      icon: <TimesCircleIcon />,
      enabled: config?.features.REPO_MIRROR,
    },
  ];

  return {
    events: events,
  };
}
