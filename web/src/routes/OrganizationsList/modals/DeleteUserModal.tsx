import {useState} from 'react';
import {Modal, ModalVariant, Button, Text, Alert} from '@patternfly/react-core';
import {useDeleteUser} from 'src/hooks/UseUserActions';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';

interface DeleteUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  username: string;
}

export default function DeleteUserModal(props: DeleteUserModalProps) {
  const [error, setError] = useState<string | null>(null);
  const {addAlert} = useAlerts();

  const {deleteUser, isLoading} = useDeleteUser({
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully deleted user ${props.username}`,
      });
      handleClose();
    },
    onError: (err) => {
      const errorMessage =
        err?.response?.data?.error_message || 'Failed to delete user';
      setError(errorMessage);
      addAlert({
        variant: AlertVariant.Failure,
        title: `Failed to delete user ${props.username}`,
        message: errorMessage,
      });
    },
  });

  const handleClose = () => {
    setError(null);
    props.onClose();
  };

  const handleDelete = () => {
    setError(null);
    deleteUser(props.username);
  };

  return (
    <Modal
      title="Delete User"
      isOpen={props.isOpen}
      onClose={handleClose}
      variant={ModalVariant.medium}
      actions={[
        <Button
          key="delete"
          variant="danger"
          onClick={handleDelete}
          isLoading={isLoading}
          isDisabled={isLoading}
        >
          Delete User
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>,
      ]}
    >
      <Text>
        Are you sure you want to delete user <strong>{props.username}</strong>?
      </Text>
      <Alert
        variant="warning"
        title="Warning"
        isInline
        style={{marginTop: 16}}
      >
        This action cannot be undone. All repositories and data owned by this
        user will be permanently deleted.
      </Alert>
      {error && (
        <Alert variant="danger" title="Error" isInline style={{marginTop: 16}}>
          {error}
        </Alert>
      )}
    </Modal>
  );
}
