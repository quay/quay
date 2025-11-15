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
import {useChangeUserEmail} from 'src/hooks/UseUserActions';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {isFreshLoginError} from 'src/utils/freshLoginErrors';

interface ChangeEmailModalProps {
  isOpen: boolean;
  onClose: () => void;
  username: string;
}

export default function ChangeEmailModal(props: ChangeEmailModalProps) {
  const [newEmail, setNewEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const {addAlert} = useUI();

  const {changeEmail, isLoading} = useChangeUserEmail({
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully changed email for ${props.username}`,
      });
      handleClose();
    },
    onError: (err) => {
      const errorMessage =
        err?.response?.data?.error_message ||
        err?.message ||
        'Failed to change email';
      // Filter out fresh login errors to prevent duplicate alerts
      if (isFreshLoginError(errorMessage)) {
        return;
      }
      setError(errorMessage);
      addAlert({
        variant: AlertVariant.Failure,
        title: `Failed to change email for ${props.username}`,
        message: errorMessage,
      });
    },
  });

  const handleClose = () => {
    setNewEmail('');
    setError(null);
    props.onClose();
  };

  const handleSubmit = () => {
    if (!newEmail.trim()) {
      setError('Email cannot be empty');
      return;
    }
    // Basic email validation
    const emailRegex = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i;
    if (!emailRegex.test(newEmail.trim())) {
      setError('Please enter a valid email address');
      return;
    }
    setError(null);
    changeEmail(props.username, newEmail.trim());
    // Close modal; request is queued if fresh login required
    handleClose();
  };

  return (
    <Modal
      title={`Change Email for ${props.username}`}
      isOpen={props.isOpen}
      onClose={handleClose}
      variant={ModalVariant.medium}
      actions={[
        <Button
          key="confirm"
          variant="primary"
          onClick={handleSubmit}
          isLoading={isLoading}
          isDisabled={isLoading || !newEmail.trim()}
        >
          Change Email
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>,
      ]}
    >
      <Form>
        <FormGroup label="Enter new email address:" isRequired>
          <TextInput
            id="new-email"
            value={newEmail}
            onChange={(_event, value) => setNewEmail(value)}
            placeholder="user@example.com"
            type="email"
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
