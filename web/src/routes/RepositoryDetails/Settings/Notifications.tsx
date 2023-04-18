import {
  Button,
  ClipboardCopy,
  ClipboardCopyVariant,
  Flex,
  FlexItem,
  Spinner,
} from '@patternfly/react-core';
import {BellIcon} from '@patternfly/react-icons';
import {
  ExpandableRowContent,
  TableComposable,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '@patternfly/react-table';
import {useEffect, useState} from 'react';
import Conditional from 'src/components/empty/Conditional';
import Empty from 'src/components/empty/Empty';
import ReadonlySecret from 'src/components/ReadonlySecret';
import {useEvents} from 'src/hooks/UseEvents';
import {useNotificationMethods} from 'src/hooks/UseNotificationMethods';
import {useNotifications} from 'src/hooks/UseNotifications';
import {
  NotificationEventType,
  NotificationMethodType,
  RepoNotification,
  isNotificationEnabled,
} from 'src/resources/NotificationResource';
import {DrawerContentType} from '../Types';
import {NotificationsColumnNames} from './ColumnNames';
import NotificationsKebab from './NotificationsKebab';
import NotificationsToolbar from './NotificationsToolbar';

export default function Notifications({
  org,
  repo,
  ...props
}: NotificationsProps) {
  const [selectedNotifications, setSelectedNotifications] = useState<
    RepoNotification[]
  >([]);
  const [expandedUuids, setExpandedUuids] = useState<string[]>([]);
  const {
    notifications,
    loading,
    error,
    paginatedNotifications,
    page,
    setPage,
    perPage,
    setPerPage,
    filter,
    setFilter,
    resetFilter,
  } = useNotifications(org, repo);

  const isExpanded = (uuid: string) => expandedUuids.includes(uuid);
  const setExpanded = (uuid: string, isExpanding = true) =>
    setExpandedUuids((prevExpanded) => {
      const otherExpandedRepoNames = prevExpanded.filter((u) => u !== uuid);
      return isExpanding
        ? [...otherExpandedRepoNames, uuid]
        : otherExpandedRepoNames;
    });

  const onSelectNotification = (
    notification: RepoNotification,
    rowIndex: number,
    isSelecting: boolean,
  ) => {
    setSelectedNotifications((prevSelected) => {
      const others = prevSelected.filter((r) => r.uuid !== notification.uuid);
      return isSelecting ? [...others, notification] : others;
    });
  };

  // Close drawer if navigating away from notification settings
  useEffect(() => {
    return () => {
      props.setDrawerContent(DrawerContentType.None);
    };
  }, []);

  if (loading) {
    return <Spinner />;
  }

  if (error) {
    return <>Unable to load notifications</>;
  }

  if (notifications && notifications.length == 0) {
    return (
      <Empty
        icon={BellIcon}
        title="No notifications found"
        body="No notifications have been setup for this repository"
        button={
          <Button
            onClick={() =>
              props.setDrawerContent(DrawerContentType.CreateNotification)
            }
          >
            Create Notification
          </Button>
        }
      />
    );
  }

  return (
    <>
      <NotificationsToolbar
        org={org}
        repo={repo}
        allItems={notifications}
        paginatedItems={paginatedNotifications}
        selectedItems={selectedNotifications}
        page={page}
        setPage={setPage}
        perPage={perPage}
        setPerPage={setPerPage}
        onItemSelect={onSelectNotification}
        deselectAll={() => setSelectedNotifications([])}
        setDrawerContent={props.setDrawerContent}
        filter={filter}
        setFilter={setFilter}
        resetFilter={resetFilter}
      />
      <TableComposable aria-label="Repository notifications table">
        <Thead>
          <Tr>
            <Th />
            <Th />
            <Th>{NotificationsColumnNames.title}</Th>
            <Th>{NotificationsColumnNames.event}</Th>
            <Th>{NotificationsColumnNames.notification}</Th>
            <Th>{NotificationsColumnNames.status}</Th>
            <Th />
          </Tr>
        </Thead>
        {paginatedNotifications?.map((notification, rowIndex) => (
          <Tbody
            key={notification.uuid}
            isExpanded={isExpanded(notification.uuid)}
          >
            <Tr>
              <Td
                expand={{
                  rowIndex,
                  isExpanded: isExpanded(notification.uuid),
                  onToggle: () =>
                    setExpanded(
                      notification.uuid,
                      !isExpanded(notification.uuid),
                    ),
                }}
              />
              <Td
                select={{
                  rowIndex,
                  onSelect: (e, isSelecting) =>
                    onSelectNotification(notification, rowIndex, isSelecting),
                  isSelected: selectedNotifications.some(
                    (n) => n.uuid === notification.uuid,
                  ),
                }}
              />
              <Td data-label="title">
                {notification.title ? notification.title : '(Untitled)'}
              </Td>
              <Td data-label="event">
                <EventTitle type={notification.event} />
              </Td>
              <Td data-label="notification">
                <NotificationTitle notification={notification} />
              </Td>
              <Td data-label="status">
                <NotificationStatus notification={notification} />
              </Td>
              <Td data-label="kebab">
                <NotificationsKebab
                  org={org}
                  repo={repo}
                  notification={notification}
                />
              </Td>
            </Tr>
            <Tr isExpanded={isExpanded(notification.uuid)}>
              <Td colSpan={7} id="notification-config-details">
                <ExpandableRowContent>
                  <NotificationConfig notification={notification} />
                </ExpandableRowContent>
              </Td>
            </Tr>
          </Tbody>
        ))}
      </TableComposable>
    </>
  );
}

function EventTitle({type}: {type: NotificationEventType}) {
  const {events} = useEvents();
  const event = events.find((e) => e.type == type);
  return (
    <>
      {event.icon} <span style={{fontSize: '.8em'}}>{event.title}</span>
    </>
  );
}

function NotificationTitle({notification}: {notification: RepoNotification}) {
  const {notificationMethods} = useNotificationMethods();
  const notificationMethod = notificationMethods.find(
    (m) => m.type == notification.method,
  );
  return (
    <Flex direction={{default: 'column'}}>
      <FlexItem style={{marginBottom: 0}}>
        <i className="fa fa-lg quay-icon"></i>
        {notificationMethod.title}
      </FlexItem>
    </Flex>
  );
}

function NotificationConfig({notification}: {notification: RepoNotification}) {
  switch (notification.method) {
    case NotificationMethodType.email:
      return (
        <FlexItem id="configured-email" style={{color: 'grey'}}>
          email: {notification.config?.email}
        </FlexItem>
      );
    case NotificationMethodType.flowdock:
      return (
        <FlexItem id="flow-api-token" style={{color: 'grey'}}>
          <ReadonlySecret
            label="Flow API Token"
            secret={notification.config?.flow_api_token}
          />
        </FlexItem>
      );
    case NotificationMethodType.hipchat:
      return (
        <>
          <FlexItem
            id="hipchat-room-id"
            style={{color: 'grey', marginBottom: '0px'}}
          >
            Room ID #: {notification.config?.room_id}
          </FlexItem>
          <FlexItem id="hipchat-token" style={{color: 'grey'}}>
            <ReadonlySecret
              label="Room Notification Token"
              secret={notification.config?.notification_token}
            />
          </FlexItem>
        </>
      );
    case NotificationMethodType.slack:
      return (
        <FlexItem id="slack-url" style={{color: 'grey'}}>
          Webhook URL: {notification.config?.url}
        </FlexItem>
      );
    case NotificationMethodType.webhook:
      return (
        <>
          <FlexItem
            id="webhook-url"
            style={{color: 'grey', marginBottom: '0px'}}
          >
            Webhook URL: {notification.config?.url}
          </FlexItem>
          <Conditional if={notification.config?.template != ''}>
            <FlexItem id="webhook-body" style={{color: 'grey'}}>
              POST body template (optional):
              <ClipboardCopy
                isCode
                isReadOnly
                hoverTip="Copy"
                clickTip="Copied"
                variant={ClipboardCopyVariant.expansion}
              >
                {notification.config?.template}
              </ClipboardCopy>
            </FlexItem>
          </Conditional>
        </>
      );
    // TODO: Quay notifications not supported in new UI until
    // notification header has been implemented
    // case NotificationMethodType.quaynotification:
    //   return (
    //     <Flex direction={{default: 'column'}}>
    //       <FlexItem style={{marginBottom: 0}}>
    //         {notificationMethod.title}
    //       </FlexItem>
    //     </Flex>
    //   );
  }
}

function NotificationStatus({notification}: {notification: RepoNotification}) {
  return isNotificationEnabled(notification) ? (
    <>Enabled</>
  ) : (
    <>Disabled (3 failed attempts)</>
  );
}

interface NotificationsProps {
  org: string;
  repo: string;
  setDrawerContent: (content: DrawerContentType) => void;
}
