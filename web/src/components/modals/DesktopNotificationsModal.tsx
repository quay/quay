import React from 'react';
import {
  Button,
  Modal,
  ModalVariant,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@patternfly/react-core';

interface DesktopNotificationsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isEnabling: boolean; // true for "turn on", false for "turn off"
}

export default function DesktopNotificationsModal({
  isOpen,
  onClose,
  onConfirm,
  isEnabling,
}: DesktopNotificationsModalProps) {
  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  return (
    <Modal
      variant={ModalVariant.small}
      isOpen={isOpen}
      onClose={onClose}
      data-testid="desktop-notifications-modal"
    >
      <ModalHeader
        title={
          isEnabling
            ? 'Enable Desktop Notifications'
            : 'Disable Desktop Notifications'
        }
      />
      <ModalBody>
        <p>
          Are you sure you want to turn {isEnabling ? 'on' : 'off'} desktop
          notifications?
        </p>
      </ModalBody>
      <ModalFooter>
        <Button
          key="confirm"
          variant="primary"
          onClick={handleConfirm}
          data-testid="notification-confirm"
        >
          OK
        </Button>
        <Button
          key="cancel"
          variant="link"
          onClick={onClose}
          data-testid="notification-cancel"
        >
          Cancel
        </Button>
      </ModalFooter>
    </Modal>
  );
}
