import {useState} from 'react';
import {Modal, ModalVariant, Button, Text, Alert} from '@patternfly/react-core';
import {useTakeOwnership} from 'src/hooks/UseOrganizationActions';
import {AlertVariant, useUI} from 'src/contexts/UIContext';

interface TakeOwnershipModalProps {
  isOpen: boolean;
  onClose: () => void;
  organizationName: string;
  isUser: boolean;
}

export default function TakeOwnershipModal(props: TakeOwnershipModalProps) {
  const [error, setError] = useState<string | null>(null);
  const {addAlert} = useUI();
  const entityType = props.isUser ? 'user' : 'organization';

  const {takeOwnership, isLoading} = useTakeOwnership({
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully took ownership of ${entityType} ${props.organizationName}`,
      });
      handleClose();
    },
    onError: (err) => {
      const errorMessage =
        err?.response?.data?.error_message ||
        err?.message ||
        'Failed to take ownership';
      // Ignore errors from cancelled fresh login verification
      if (errorMessage === 'Fresh login verification cancelled') {
        return;
      }
      setError(errorMessage);
      addAlert({
        variant: AlertVariant.Failure,
        title: `Failed to take ownership of ${entityType} ${props.organizationName}`,
        message: errorMessage,
      });
    },
  });

  const handleClose = () => {
    setError(null);
    props.onClose();
  };

  const handleTakeOwnership = () => {
    setError(null);
    takeOwnership(props.organizationName);
    // Close modal immediately after submitting the request
    // If fresh login is required, the request will be queued and retried after verification
    handleClose();
  };

  return (
    <Modal
      title="Take Ownership"
      isOpen={props.isOpen}
      onClose={handleClose}
      variant={ModalVariant.medium}
      actions={[
        <Button
          key="confirm"
          variant="primary"
          onClick={handleTakeOwnership}
          isLoading={isLoading}
          isDisabled={isLoading}
        >
          Take Ownership
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>,
      ]}
    >
      <Text>
        Are you sure you want to take ownership of {entityType}{' '}
        <strong>{props.organizationName}</strong>?
      </Text>
      {props.isUser && (
        <Alert
          variant="warning"
          title="Note"
          isInline
          style={{marginTop: 16}}
        >
          This will convert the user namespace into an organization.{' '}
          <strong>
            The user will no longer be able to login to this account.
          </strong>
        </Alert>
      )}
      {error && (
        <Alert
          variant="danger"
          title="Error"
          isInline
          style={{marginTop: 16}}
        >
          {error}
        </Alert>
      )}
    </Modal>
  );
}
