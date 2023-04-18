import {
  Alert,
  AlertActionCloseButton,
  AlertGroup,
  Button,
  Dropdown,
  DropdownItem,
  KebabToggle,
  Modal,
  ModalVariant,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
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
  const [isOpen, setIsOpen] = useState<boolean>();
  const [isTestModalOpen, setIsTestModalOpen] = useState<boolean>(false);
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
        toggle={
          <KebabToggle
            onToggle={() => {
              setIsOpen(!isOpen);
            }}
          />
        }
        isOpen={isOpen}
        dropdownItems={[
          <DropdownItem key="test" onClick={() => test(notification.uuid)}>
            Test Notification
          </DropdownItem>,
          <DropdownItem
            key="delete"
            onClick={() => deleteNotifications(notification.uuid)}
          >
            Delete Notification
          </DropdownItem>,
          <Conditional key="enable" if={isNotificationDisabled(notification)}>
            <DropdownItem
              onClick={() => enableNotifications(notification.uuid)}
            >
              Enable Notification
            </DropdownItem>
          </Conditional>,
        ]}
        isPlain
      />
    </>
  );
}

interface NotificationsKebabProps {
  org: string;
  repo: string;
  notification: RepoNotification;
}
