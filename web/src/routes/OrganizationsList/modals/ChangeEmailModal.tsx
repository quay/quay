import {useState, useEffect} from 'react';
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
import {useChangeEmail} from 'src/hooks/UseCurrentUser';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {isFreshLoginError} from 'src/utils/freshLoginErrors';

interface ChangeEmailModalProps {
  isOpen: boolean;
  onClose: () => void;
  username: string;
  currentEmail?: string; // Current email to pre-fill
  isSuperuserMode?: boolean; // Default true for backward compatibility
}

export default function ChangeEmailModal(props: ChangeEmailModalProps) {
  const [newEmail, setNewEmail] = useState(props.currentEmail || '');
  const [error, setError] = useState<string | null>(null);
  const {addAlert} = useUI();
  const isSuperuserMode = props.isSuperuserMode ?? true; // Default to true

  // Superuser mode hook
  const {changeEmail: changeUserEmailSuperuser, isLoading: isLoadingSuperuser} =
    useChangeUserEmail({
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

  // User self-service mode hook
  const {changeEmail: changeUserEmailSelf, isLoading: isLoadingSelf} =
    useChangeEmail({
      onSuccess: () => {
        addAlert({
          variant: AlertVariant.Success,
          title: 'Verification email sent',
          message: `An email has been sent to ${newEmail}. Please click the Confirm button to apply the email change.`,
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
          title: 'Failed to change email',
          message: errorMessage,
        });
      },
    });

  const isLoading = isSuperuserMode ? isLoadingSuperuser : isLoadingSelf;

  // Reset email when modal opens/closes
  useEffect(() => {
    if (props.isOpen) {
      setNewEmail(props.currentEmail || '');
      setError(null);
    }
  }, [props.isOpen, props.currentEmail]);

  const handleClose = () => {
    setNewEmail(props.currentEmail || '');
    setError(null);
    props.onClose();
  };

  const handleSubmit = () => {
    if (!newEmail.trim()) {
      setError('Email cannot be empty');
      return;
    }

    // Check if email is the same as current
    if (newEmail.trim() === props.currentEmail) {
      setError('Please enter a different email address');
      return;
    }

    // Basic email validation
    const emailRegex = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i;
    if (!emailRegex.test(newEmail.trim())) {
      setError('Please enter a valid email address');
      return;
    }
    setError(null);

    if (isSuperuserMode) {
      changeUserEmailSuperuser(props.username, newEmail.trim());
    } else {
      changeUserEmailSelf(newEmail.trim());
    }
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
        <FormGroup
          label="Please enter a new email address. A verification email will be sent before the change is applied."
          isRequired
        >
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
