import {useEffect, useState} from 'react';
import {
  Alert,
  AlertActionCloseButton,
  AlertGroup,
  Button,
  Dropdown,
  DropdownItem,
  DropdownList,
  MenuToggle,
  MenuToggleElement,
  Modal,
  ModalVariant,
} from '@patternfly/react-core';
import EllipsisVIcon from '@patternfly/react-icons/dist/esm/icons/ellipsis-v-icon';
import {useUpdateNotifications} from 'src/hooks/UseUpdateNotifications';
import Conditional from 'src/components/empty/Conditional';
import {
  isNotificationDisabled,
  RepoNotification,
} from 'src/resources/NotificationResource';

export default function NotificationsKebab({
  org,
  repo,
  notification,
}: NotificationsKebabProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const {
    deleteNotifications,
    errorDeletingNotification,
    resetDeletingNotification,
    test,
    successTestingNotification,
    errorTestingNotification,
    resetTestingNotification,
    enableNotifications,
    errorEnablingNotification,
    resetEnablingNotification,
  } = useUpdateNotifications(org, repo);

  useEffect(() => {
    if (successTestingNotification) {
      setIsTestModalOpen(true);
      resetTestingNotification();
    }
  }, [successTestingNotification]);

  return (
    <>
      <Conditional if={errorDeletingNotification}>
        <AlertGroup isToast isLiveRegion>
          <Alert
            variant="danger"
            title={`Unable to delete notification ${notification.title}`}
            actionClose={
              <AlertActionCloseButton onClose={resetDeletingNotification} />
            }
          />
        </AlertGroup>
      </Conditional>
      <Conditional if={errorTestingNotification}>
        <AlertGroup isToast isLiveRegion>
          <Alert
            variant="danger"
            title={`Unable to test notification ${notification.title}`}
            actionClose={
              <AlertActionCloseButton onClose={resetTestingNotification} />
            }
          />
        </AlertGroup>
      </Conditional>
      <Conditional if={errorEnablingNotification}>
        <AlertGroup isToast isLiveRegion>
          <Alert
            variant="danger"
            title={`Unable to enable notification ${notification.title}`}
            actionClose={
              <AlertActionCloseButton onClose={resetEnablingNotification} />
            }
          />
        </AlertGroup>
      </Conditional>
      <Modal
        variant={ModalVariant.small}
        title="Test Notification Queued"
        isOpen={isTestModalOpen}
        onClose={() => setIsTestModalOpen(false)}
        actions={[
          <Button
            key="cancel"
            variant="primary"
            onClick={() => setIsTestModalOpen(false)}
          >
            Close
          </Button>,
        ]}
      >
        A test version of this notification has been queued and should appear
        shortly
      </Modal>
      <Dropdown
        onSelect={() => setIsOpen(false)}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            variant="plain"
            id={`${notification.uuid}-toggle-kebab`}
            data-testid={`${notification.uuid}-toggle-kebab`}
            onClick={() => setIsOpen(() => !isOpen)}
            isExpanded={isOpen}
          >
            <EllipsisVIcon />
          </MenuToggle>
        )}
        isOpen={isOpen}
        onOpenChange={(isOpen) => setIsOpen(isOpen)}
        shouldFocusToggleOnSelect
      >
        <DropdownList>
          <DropdownItem onClick={() => test(notification.uuid)}>
            Test Notification
          </DropdownItem>

          <DropdownItem onClick={() => deleteNotifications(notification.uuid)}>
            Delete Notification
          </DropdownItem>

          <Conditional if={isNotificationDisabled(notification)}>
            <DropdownItem
              onClick={() => enableNotifications(notification.uuid)}
            >
              Enable Notification
            </DropdownItem>
          </Conditional>
        </DropdownList>
      </Dropdown>
    </>
  );
}

interface NotificationsKebabProps {
  org: string;
  repo: string;
  notification: RepoNotification;
}
