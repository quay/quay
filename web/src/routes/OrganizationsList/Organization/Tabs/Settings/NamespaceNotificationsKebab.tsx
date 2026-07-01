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
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
} from '@patternfly/react-core';
import EllipsisVIcon from '@patternfly/react-icons/dist/esm/icons/ellipsis-v-icon';
import Conditional from 'src/components/empty/Conditional';
import {useUpdateNamespaceNotifications} from 'src/hooks/UseUpdateNamespaceNotifications';
import {
  isNamespaceNotificationDisabled,
  NamespaceNotification,
} from 'src/resources/NamespaceNotificationResource';

export default function NamespaceNotificationsKebab({
  orgname,
  isUser = false,
  notification,
}: NamespaceNotificationsKebabProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
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
  } = useUpdateNamespaceNotifications(orgname, isUser);

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
            title={`Unable to delete notification ${notification.title || '(Untitled)'}`}
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
            title={`Unable to test notification ${notification.title || '(Untitled)'}`}
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
            title={`Unable to enable notification ${notification.title || '(Untitled)'}`}
            actionClose={
              <AlertActionCloseButton onClose={resetEnablingNotification} />
            }
          />
        </AlertGroup>
      </Conditional>

      <Modal
        variant={ModalVariant.small}
        isOpen={isTestModalOpen}
        onClose={() => setIsTestModalOpen(false)}
      >
        <ModalHeader title="Test Notification Queued" />
        <ModalBody>
          A test version of this notification has been queued and should appear
          shortly
        </ModalBody>
        <ModalFooter>
          <Button
            key="close"
            variant="primary"
            onClick={() => setIsTestModalOpen(false)}
          >
            Close
          </Button>
        </ModalFooter>
      </Modal>

      <Modal
        variant={ModalVariant.small}
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
      >
        <ModalHeader title="Delete Notification" />
        <ModalBody>
          Are you sure you want to delete the notification &ldquo;
          {notification.title || '(Untitled)'}&rdquo;?
        </ModalBody>
        <ModalFooter>
          <Button
            key="confirm"
            variant="danger"
            data-testid="confirm-delete-ns-notification"
            onClick={() => {
              deleteNotifications(notification.uuid);
              setIsDeleteModalOpen(false);
            }}
          >
            Delete
          </Button>
          <Button
            key="cancel"
            variant="link"
            onClick={() => setIsDeleteModalOpen(false)}
          >
            Cancel
          </Button>
        </ModalFooter>
      </Modal>

      <Dropdown
        onSelect={() => setIsOpen(false)}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            variant="plain"
            id={`${notification.uuid}-ns-toggle-kebab`}
            data-testid={`${notification.uuid}-ns-toggle-kebab`}
            onClick={() => setIsOpen((prev) => !prev)}
            isExpanded={isOpen}
          >
            <EllipsisVIcon />
          </MenuToggle>
        )}
        isOpen={isOpen}
        onOpenChange={setIsOpen}
        shouldFocusToggleOnSelect
      >
        <DropdownList>
          <DropdownItem
            data-testid={`${notification.uuid}-test-notification`}
            onClick={() => test(notification.uuid)}
          >
            Test Notification
          </DropdownItem>
          <DropdownItem
            data-testid={`${notification.uuid}-delete-notification`}
            onClick={() => setIsDeleteModalOpen(true)}
          >
            Delete Notification
          </DropdownItem>
          <Conditional if={isNamespaceNotificationDisabled(notification)}>
            <DropdownItem
              data-testid={`${notification.uuid}-enable-notification`}
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

interface NamespaceNotificationsKebabProps {
  orgname: string;
  isUser?: boolean;
  notification: NamespaceNotification;
}
