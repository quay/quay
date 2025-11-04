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
import {useFreshLogin} from 'src/hooks/UseFreshLogin';
import {FreshLoginModal} from 'src/components/modals/FreshLoginModal';

interface ChangeEmailModalProps {
  isOpen: boolean;
  onClose: () => void;
  username: string;
}

export default function ChangeEmailModal(props: ChangeEmailModalProps) {
  const [newEmail, setNewEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const {addAlert} = useUI();

  const {
    isModalOpen: isFreshLoginModalOpen,
    isLoading: isFreshLoginLoading,
    error: freshLoginError,
    showFreshLoginModal,
    handleVerify,
    handleCancel: handleFreshLoginCancel,
    isFreshLoginRequired,
  } = useFreshLogin();

  const {changeEmail, isLoading} = useChangeUserEmail({
    onSuccess: () => {
      addAlert({
        variant: AlertVariant.Success,
        title: `Successfully changed email for ${props.username}`,
      });
      handleClose();
    },
    onError: (err) => {
      // Check if fresh login is required
      if (isFreshLoginRequired(err)) {
        // Show fresh login modal and retry on success
        showFreshLoginModal(() => changeEmail(props.username, newEmail.trim()));
        return;
      }

      const errorMessage =
        err?.response?.data?.error_message || 'Failed to change email';
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
  };

  return (
    <>
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
      <FreshLoginModal
        isOpen={isFreshLoginModalOpen}
        onVerify={handleVerify}
        onCancel={handleFreshLoginCancel}
        isLoading={isFreshLoginLoading}
        error={freshLoginError}
      />
    </>
  );
}
