import React from 'react';
import {Modal, ModalVariant, Button, Text} from '@patternfly/react-core';

interface SessionExpiredModalProps {
  isOpen: boolean;
  onSignIn: () => void;
}

export function SessionExpiredModal({
  isOpen,
  onSignIn,
}: SessionExpiredModalProps) {
  return (
    <Modal
      variant={ModalVariant.small}
      title="Session Expired"
      isOpen={isOpen}
      onClose={onSignIn}
      actions={[
        <Button key="signin" variant="primary" onClick={onSignIn}>
          Sign In
        </Button>,
      ]}
    >
      <Text>Your user session has expired. Please sign in to continue.</Text>
    </Modal>
  );
}
