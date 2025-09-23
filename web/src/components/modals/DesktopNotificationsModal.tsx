import React from 'react';
import {Modal, ModalVariant, Button} from '@patternfly/react-core';

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
      title="Confirm"
      isOpen={isOpen}
      onClose={onClose}
      actions={[
        <Button key="confirm" variant="primary" onClick={handleConfirm}>
          OK
        </Button>,
        <Button key="cancel" variant="link" onClick={onClose}>
          Cancel
        </Button>,
      ]}
    >
      <p>
        Are you sure you want to turn {isEnabling ? 'on' : 'off'} browser
        notifications?
      </p>
    </Modal>
  );
}
