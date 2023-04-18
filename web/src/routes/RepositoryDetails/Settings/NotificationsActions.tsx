import {
  Alert,
  AlertActionCloseButton,
  AlertGroup,
  Dropdown,
  DropdownItem,
  DropdownToggle,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import Conditional from 'src/components/empty/Conditional';
import {useUpdateNotifications} from 'src/hooks/UseUpdateNotifications';
import {
  isNotificationDisabled,
  RepoNotification,
} from 'src/resources/NotificationResource';

export default function Actions(props: ActionsProps) {
  const [isOpen, setIsOpen] = useState<boolean>(false);

  const {
    enableNotifications,
    successEnablingNotification,
    errorEnablingNotification,
    resetEnablingNotification,
    deleteNotifications,
    errorDeletingNotification,
    successDeletingNotification,
    resetDeletingNotification,
  } = useUpdateNotifications(props.org, props.repo);

  useEffect(() => {
    if (successEnablingNotification) {
      props.deselectAll();
      resetEnablingNotification();
    }
  }, [successEnablingNotification]);

  useEffect(() => {
    if (successDeletingNotification) {
      props.deselectAll();
      resetDeletingNotification();
    }
  }, [successDeletingNotification]);

  const disabledNotifications: RepoNotification[] = props.selectedItems.filter(
    (n) => isNotificationDisabled(n),
  );
  const notificationsToEnable: string[] = disabledNotifications.map(
    (n) => n.uuid,
  );

  return (
    <>
      <Conditional if={errorDeletingNotification}>
        <AlertGroup isToast isLiveRegion>
          <Alert
            variant="danger"
            title="Unable to bulk delete notifications"
            actionClose={
              <AlertActionCloseButton onClose={resetDeletingNotification} />
            }
          />
        </AlertGroup>
      </Conditional>
      <Conditional if={errorEnablingNotification}>
        <AlertGroup isToast isLiveRegion>
          <Alert
            variant="danger"
            title="Unable to bulk delete notifications"
            actionClose={
              <AlertActionCloseButton onClose={resetEnablingNotification} />
            }
          />
        </AlertGroup>
      </Conditional>
      <Dropdown
        onSelect={() => setIsOpen(false)}
        toggle={
          <DropdownToggle
            isDisabled={props.isDisabled}
            onToggle={(isOpen) => setIsOpen(isOpen)}
          >
            Actions
          </DropdownToggle>
        }
        isOpen={isOpen}
        dropdownItems={[
          <Conditional
            key="notifications-bulk-delete"
            if={notificationsToEnable.length > 0}
          >
            <DropdownItem
              onClick={() => enableNotifications(notificationsToEnable)}
            >
              Enable
            </DropdownItem>
          </Conditional>,
          <DropdownItem
            key="notifications-bulk-delete"
            id="bulk-delete-notifications"
            onClick={() => {
              deleteNotifications(props.selectedItems.map((n) => n.uuid));
            }}
          >
            Delete
          </DropdownItem>,
        ]}
      />
    </>
  );
}

interface ActionsProps {
  isDisabled?: boolean;
  org: string;
  repo: string;
  selectedItems: RepoNotification[];
  deselectAll: () => void;
}
