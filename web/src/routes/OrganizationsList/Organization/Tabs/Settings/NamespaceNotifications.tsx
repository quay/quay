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
import RequestError from 'src/components/errors/RequestError';
import {ToolbarPagination} from 'src/components/toolbar/ToolbarPagination';
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
import {useSuperuserPermissions} from 'src/hooks/UseSuperuserPermissions';

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
        <FlexItem style={{color: 'var(--pf-t--global--text--color--subtle)'}}>
          Sent to namespace contact or admin emails
        </FlexItem>
      );
    case NamespaceNotificationMethodType.slack:
      return (
        <FlexItem style={{color: 'var(--pf-t--global--text--color--subtle)'}}>
          Webhook URL: {String(notification.config?.url ?? '')}
        </FlexItem>
      );
    case NamespaceNotificationMethodType.webhook:
      return (
        <>
          <FlexItem
            style={{
              color: 'var(--pf-t--global--text--color--subtle)',
              marginBottom: 0,
            }}
          >
            Webhook URL: {String(notification.config?.url ?? '')}
          </FlexItem>
          <Conditional if={notification.config?.template !== ''}>
            <FlexItem
              style={{color: 'var(--pf-t--global--text--color--subtle)'}}
            >
              POST body template (optional):
              <ClipboardCopy
                isCode
                isReadOnly
                hoverTip="Copy"
                clickTip="Copied"
                variant={ClipboardCopyVariant.expansion}
              >
                {String(notification.config?.template ?? '')}
              </ClipboardCopy>
            </FlexItem>
          </Conditional>
        </>
      );
    case NamespaceNotificationMethodType.quaynotification: {
      const target = notification.config?.target as
        | Record<string, unknown>
        | undefined;
      return (
        <FlexItem style={{color: 'var(--pf-t--global--text--color--subtle)'}}>
          Recipient: {String(target?.name ?? '')}
        </FlexItem>
      );
    }
    default:
      return null;
  }
}

export default function NamespaceNotifications({
  organizationName,
  isUser = false,
}: NamespaceNotificationsProps) {
  const {isReadOnlySuperUser} = useSuperuserPermissions();
  const config = useQuayConfig();
  const registryTitle = config?.config?.REGISTRY_TITLE_SHORT || 'Quay';
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [expandedUuids, setExpandedUuids] = useState<string[]>([]);

  const {notifications, loading, error} = useNamespaceNotifications(
    organizationName,
    isUser,
  );

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
    return <RequestError message="Unable to load notifications" />;
  }

  if (notifications && notifications.length === 0) {
    return (
      <>
        <Empty
          icon={BellIcon}
          title="No notifications configured"
          body="Configure notifications to receive alerts when quota thresholds are crossed"
          button={
            !isReadOnlySuperUser ? (
              <Button
                data-testid="create-ns-notification-btn"
                onClick={() => setIsCreateOpen(true)}
              >
                Create notification
              </Button>
            ) : null
          }
        />
        <NamespaceNotificationsCreateForm
          orgname={organizationName}
          isUser={isUser}
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
          {!isReadOnlySuperUser && (
            <ToolbarItem>
              <Button
                data-testid="create-ns-notification-btn"
                onClick={() => setIsCreateOpen(true)}
              >
                Create notification
              </Button>
            </ToolbarItem>
          )}
          <ToolbarPagination
            total={paginationProps.total}
            perPage={paginationProps.perPage}
            page={paginationProps.page}
            setPage={paginationProps.setPage}
            setPerPage={paginationProps.setPerPage}
            data-testid="ns-notifications-pagination"
          />
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
            <Th modifier="nowrap" sort={getSortableSort(0)}>
              Title
            </Th>
            <Th modifier="nowrap" sort={getSortableSort(1)}>
              Event
            </Th>
            <Th modifier="nowrap" sort={getSortableSort(2)}>
              Method
            </Th>
            <Th modifier="nowrap" sort={getSortableSort(3)}>
              Status
            </Th>
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
                {!isReadOnlySuperUser && (
                  <NamespaceNotificationsKebab
                    orgname={organizationName}
                    isUser={isUser}
                    notification={notification}
                  />
                )}
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
        isUser={isUser}
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
      />
    </>
  );
}

interface NamespaceNotificationsProps {
  organizationName: string;
  isUser?: boolean;
}
