import {useState} from 'react';
import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  TextInput,
  Alert,
} from '@patternfly/react-core';
import {useChangeUserPassword} from 'src/hooks/UseUserActions';
import {AlertVariant, useUI} from 'src/contexts/UIContext';

interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
  username: string;
}

export default function ChangePasswordModal(props: ChangePasswordModalProps) {
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const {addAlert} = useUI();

  const {changePassword, isLoading} = useChangeUserPassword({
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully changed password for ${props.username}`,
      });
      handleClose();
    },
    onError: (err) => {
      const errorMessage =
        err?.response?.data?.error_message || 'Failed to change password';
      setError(errorMessage);
      addAlert({
        variant: AlertVariant.Failure,
        title: `Failed to change password for ${props.username}`,
        message: errorMessage,
      });
    },
  });

  const handleClose = () => {
    setNewPassword('');
    setError(null);
    props.onClose();
  };

  const handleSubmit = () => {
    if (!newPassword) {
      setError('Password cannot be empty');
      return;
    }
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    setError(null);
    changePassword(props.username, newPassword);
  };

  return (
    <Modal
      title={`Change Password for ${props.username}`}
      isOpen={props.isOpen}
      onClose={handleClose}
      variant={ModalVariant.medium}
      actions={[
        <Button
          key="confirm"
          variant="primary"
          onClick={handleSubmit}
          isLoading={isLoading}
          isDisabled={isLoading || !newPassword}
        >
          Change Password
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>,
      ]}
    >
      <Form>
        <FormGroup label="Enter new password:" isRequired>
          <TextInput
            id="new-password"
            value={newPassword}
            onChange={(_event, value) => setNewPassword(value)}
            placeholder="New password (min 8 characters)"
            type="password"
            isDisabled={isLoading}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSubmit();
              }
            }}
          />
        </FormGroup>
        {error && (
          <Alert variant="danger" title="Error" isInline>
            {error}
          </Alert>
        )}
      </Form>
    </Modal>
  );
}
