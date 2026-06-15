import {useState} from 'react';
import {
  Button,
  ClipboardCopy,
  ClipboardCopyVariant,
  Flex,
  FlexItem,
  Spinner,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {BellIcon} from '@patternfly/react-icons';
import {
  ExpandableRowContent,
  Table,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '@patternfly/react-table';
import Empty from 'src/components/empty/Empty';
import Conditional from 'src/components/empty/Conditional';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useNamespaceNotifications} from 'src/hooks/UseNamespaceNotifications';
import {usePaginatedSortableTable} from 'src/hooks/usePaginatedSortableTable';
import {
  isNamespaceNotificationEnabled,
  NamespaceNotification,
  NamespaceNotificationEventType,
  NamespaceNotificationMethodType,
} from 'src/resources/NamespaceNotificationResource';
import NamespaceNotificationsCreateForm from './NamespaceNotificationsCreateForm';
import NamespaceNotificationsKebab from './NamespaceNotificationsKebab';

const EVENT_TITLES: Record<NamespaceNotificationEventType, string> = {
  [NamespaceNotificationEventType.quotaWarning]: 'Quota Warning',
  [NamespaceNotificationEventType.quotaError]: 'Quota Error',
};

function getMethodTitle(
  method: NamespaceNotificationMethodType,
  registryTitle: string,
): string {
  switch (method) {
    case NamespaceNotificationMethodType.email:
      return 'Email Notification';
    case NamespaceNotificationMethodType.slack:
      return 'Slack Notification';
    case NamespaceNotificationMethodType.webhook:
      return 'Webhook POST';
    case NamespaceNotificationMethodType.quaynotification:
      return `${registryTitle} Notification`;
    default:
      return String(method);
  }
}

function NotificationConfig({
  notification,
}: {
  notification: NamespaceNotification;
}) {
  switch (notification.method) {
    case NamespaceNotificationMethodType.email:
      return (
        <FlexItem style={{color: 'grey'}}>
          email: {(notification.config as any)?.email}
        </FlexItem>
      );
    case NamespaceNotificationMethodType.slack:
      return (
        <FlexItem style={{color: 'grey'}}>
          Webhook URL: {(notification.config as any)?.url}
        </FlexItem>
      );
    case NamespaceNotificationMethodType.webhook:
      return (
        <>
          <FlexItem style={{color: 'grey', marginBottom: '0px'}}>
            Webhook URL: {(notification.config as any)?.url}
          </FlexItem>
          <Conditional if={(notification.config as any)?.template !== ''}>
            <FlexItem style={{color: 'grey'}}>
              POST body template (optional):
              <ClipboardCopy
                isCode
                isReadOnly
                hoverTip="Copy"
                clickTip="Copied"
                variant={ClipboardCopyVariant.expansion}
              >
                {(notification.config as any)?.template}
              </ClipboardCopy>
            </FlexItem>
          </Conditional>
        </>
      );
    case NamespaceNotificationMethodType.quaynotification:
      return (
        <FlexItem style={{color: 'grey'}}>
          Recipient: {(notification.config as any)?.target?.name}
        </FlexItem>
      );
    default:
      return null;
  }
}

export default function NamespaceNotifications({
  organizationName,
}: NamespaceNotificationsProps) {
  const config = useQuayConfig();
  const registryTitle = config?.config?.REGISTRY_TITLE_SHORT || 'Quay';
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [expandedUuids, setExpandedUuids] = useState<string[]>([]);

  const {notifications, loading, error} =
    useNamespaceNotifications(organizationName);

  const {
    paginatedData: paginatedNotifications,
    getSortableSort,
    paginationProps,
  } = usePaginatedSortableTable(notifications || [], {
    columns: {
      0: (item: NamespaceNotification) => item.title || '(Untitled)',
      1: (item: NamespaceNotification) => item.event,
      2: (item: NamespaceNotification) => item.method,
      3: (item: NamespaceNotification) =>
        isNamespaceNotificationEnabled(item) ? 'Enabled' : 'Disabled',
    },
    initialPerPage: 20,
    initialSort: {columnIndex: 0, direction: 'asc'},
  });

  const isExpanded = (uuid: string) => expandedUuids.includes(uuid);
  const toggleExpanded = (uuid: string) =>
    setExpandedUuids((prev) =>
      prev.includes(uuid) ? prev.filter((u) => u !== uuid) : [...prev, uuid],
    );

  if (loading) {
    return <Spinner />;
  }

  if (error) {
    return <>Unable to load notifications</>;
  }

  if (notifications && notifications.length === 0) {
    return (
      <>
        <Empty
          icon={BellIcon}
          title="No notifications configured"
          body="Configure notifications to receive alerts when quota thresholds are crossed"
          button={
            <Button
              data-testid="create-ns-notification-btn"
              onClick={() => setIsCreateOpen(true)}
            >
              Create notification
            </Button>
          }
        />
        <NamespaceNotificationsCreateForm
          orgname={organizationName}
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
        />
      </>
    );
  }

  return (
    <>
      <Toolbar>
        <ToolbarContent>
          <ToolbarItem>
            <Button
              data-testid="create-ns-notification-btn"
              onClick={() => setIsCreateOpen(true)}
            >
              Create notification
            </Button>
          </ToolbarItem>
          <ToolbarItem variant="pagination">
            {paginationProps.total > paginationProps.perPage && (
              <span>
                {paginationProps.total} item
                {paginationProps.total !== 1 ? 's' : ''}
              </span>
            )}
          </ToolbarItem>
        </ToolbarContent>
      </Toolbar>
      <Table
        aria-label="Namespace notifications table"
        variant="compact"
        data-testid="ns-notifications-table"
      >
        <Thead>
          <Tr>
            <Th />
            <Th sort={getSortableSort(0)}>Title</Th>
            <Th sort={getSortableSort(1)}>Event</Th>
            <Th sort={getSortableSort(2)}>Method</Th>
            <Th sort={getSortableSort(3)}>Status</Th>
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
                  onToggle: () => toggleExpanded(notification.uuid),
                }}
              />
              <Td data-label="title">
                {notification.title ? notification.title : '(Untitled)'}
              </Td>
              <Td data-label="event">
                {EVENT_TITLES[notification.event] || notification.event}
              </Td>
              <Td data-label="method">
                <Flex direction={{default: 'column'}}>
                  <FlexItem style={{marginBottom: 0}}>
                    {getMethodTitle(notification.method, registryTitle)}
                  </FlexItem>
                </Flex>
              </Td>
              <Td data-label="status">
                {isNamespaceNotificationEnabled(notification) ? (
                  <>Enabled</>
                ) : (
                  <>Disabled (3 failed attempts)</>
                )}
              </Td>
              <Td data-label="kebab">
                <NamespaceNotificationsKebab
                  orgname={organizationName}
                  notification={notification}
                />
              </Td>
            </Tr>
            <Tr isExpanded={isExpanded(notification.uuid)}>
              <Td colSpan={6}>
                <ExpandableRowContent>
                  <NotificationConfig notification={notification} />
                </ExpandableRowContent>
              </Td>
            </Tr>
          </Tbody>
        ))}
      </Table>
      <NamespaceNotificationsCreateForm
        orgname={organizationName}
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />
    </>
  );
}

interface NamespaceNotificationsProps {
  organizationName: string;
}
