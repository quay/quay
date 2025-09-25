import React, {useState} from 'react';
import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  TextInput,
  Alert,
  Text,
} from '@patternfly/react-core';

interface DeleteAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  namespaceName: string;
  namespaceTitle: string; // "account" for users, "organization" for orgs
  isLoading?: boolean;
}

export default function DeleteAccountModal({
  isOpen,
  onClose,
  onConfirm,
  namespaceName,
  namespaceTitle,
  isLoading = false,
}: DeleteAccountModalProps) {
  const [verification, setVerification] = useState('');

  const handleClose = () => {
    setVerification('');
    onClose();
  };

  const handleConfirm = () => {
    if (verification === namespaceName) {
      onConfirm();
    }
  };

  const canDelete = verification === namespaceName && !isLoading;

  return (
    <Modal
      variant={ModalVariant.medium}
      title={`Delete ${namespaceTitle}`}
      isOpen={isOpen}
      onClose={handleClose}
      data-testid="delete-account-modal"
      actions={[
        <Button
          key="delete"
          variant="danger"
          onClick={handleConfirm}
          isDisabled={!canDelete}
          isLoading={isLoading}
          data-testid="delete-account-confirm"
        >
          Delete {namespaceTitle}
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>,
      ]}
    >
      <Alert
        variant="danger"
        isInline
        title="Warning"
        className="pf-v5-u-mb-md"
      >
        <p>
          Deleting an {namespaceTitle} is <strong>non-reversible</strong> and
          will delete <strong>all of the {namespaceTitle}&apos;s data</strong>{' '}
          including repositories, created build triggers, and notifications.
        </p>
      </Alert>

      <Form>
        <Text className="pf-v5-u-mb-md">
          You must type <strong>{namespaceName}</strong> below to confirm
          deletion is requested:
        </Text>

        <FormGroup fieldId="verification">
          <TextInput
            id="delete-confirmation-input"
            type="text"
            value={verification}
            onChange={(_event, value) => setVerification(value)}
            placeholder="Enter namespace here"
            isRequired
          />
        </FormGroup>
      </Form>
    </Modal>
  );
}
