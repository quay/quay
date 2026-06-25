import React, {useState} from 'react';
import {
  Button,
  Form,
  FormGroup,
  TextInput,
  Alert,
  Content,
  Modal,
  ModalVariant,
  ModalHeader,
  ModalBody,
  ModalFooter,
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
      isOpen={isOpen}
      onClose={handleClose}
      data-testid="delete-account-modal"
    >
      <ModalHeader title={`Delete ${namespaceTitle}`} />
      <ModalBody>
        <Alert
          variant="danger"
          isInline
          title="Warning"
          className="pf-v6-u-mb-md"
        >
          <p>
            Deleting an {namespaceTitle} is <strong>non-reversible</strong> and
            will delete <strong>all of the {namespaceTitle}&apos;s data</strong>{' '}
            including repositories, created build triggers, and notifications.
          </p>
        </Alert>

        <Form>
          <Content component="p" className="pf-v6-u-mb-md">
            You must type <strong>{namespaceName}</strong> below to confirm
            deletion is requested:
          </Content>

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
      </ModalBody>
      <ModalFooter>
        <Button
          key="delete"
          variant="danger"
          onClick={handleConfirm}
          isDisabled={!canDelete}
          isLoading={isLoading}
          data-testid="delete-account-confirm"
        >
          Delete {namespaceTitle}
        </Button>
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>
      </ModalFooter>
    </Modal>
  );
}
