import {useState} from 'react';
import {Modal, ModalVariant, Button, Text, Alert} from '@patternfly/react-core';
import {useToggleUserStatus} from 'src/hooks/UseUserActions';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';

interface ToggleUserStatusModalProps {
  isOpen: boolean;
  onClose: () => void;
  username: string;
  currentlyEnabled: boolean;
}

export default function ToggleUserStatusModal(
  props: ToggleUserStatusModalProps,
) {
  const [error, setError] = useState<string | null>(null);
  const {addAlert} = useAlerts();
  const action = props.currentlyEnabled ? 'disabled' : 'enabled';

  const {toggleStatus, isLoading} = useToggleUserStatus({
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully ${action} user ${props.username}`,
      });
      handleClose();
    },
    onError: (err) => {
      const errorMessage =
        err?.response?.data?.error_message || 'Failed to update user status';
      setError(errorMessage);
      addAlert({
        variant: AlertVariant.Failure,
        title: `Failed to ${action === 'disabled' ? 'disable' : 'enable'} user ${props.username}`,
        message: errorMessage,
      });
    },
  });

  const handleClose = () => {
    setError(null);
    props.onClose();
  };

  const handleToggle = () => {
    setError(null);
    toggleStatus(props.username, !props.currentlyEnabled);
  };

  const action = props.currentlyEnabled ? 'Disable' : 'Enable';
  const actionLower = action.toLowerCase();

  return (
    <Modal
      title={`${action} User`}
      isOpen={props.isOpen}
      onClose={handleClose}
      variant={ModalVariant.medium}
      actions={[
        <Button
          key="confirm"
          variant={props.currentlyEnabled ? 'warning' : 'primary'}
          onClick={handleToggle}
          isLoading={isLoading}
          isDisabled={isLoading}
        >
          {action} User
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>,
      ]}
    >
      <Text>
        Are you sure you want to {actionLower} user{' '}
        <strong>{props.username}</strong>?
      </Text>
      {props.currentlyEnabled && (
        <Alert
          variant="warning"
          title="Note"
          isInline
          style={{marginTop: 16}}
        >
          Disabling this user will prevent them from logging in and accessing
          their repositories.
        </Alert>
      )}
      {!props.currentlyEnabled && (
        <Alert variant="info" title="Note" isInline style={{marginTop: 16}}>
          Enabling this user will allow them to log in and access their
          repositories.
        </Alert>
      )}
      {error && (
        <Alert variant="danger" title="Error" isInline style={{marginTop: 16}}>
          {error}
        </Alert>
      )}
    </Modal>
  );
}
