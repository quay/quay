import React, {useState} from 'react';
import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  TextInput,
  FormHelperText,
  HelperText,
  HelperTextItem,
  Alert,
} from '@patternfly/react-core';
import {useUpdateUser} from 'src/hooks/UseCurrentUser';

interface ChangePasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type ValidationState = 'default' | 'success' | 'warning' | 'error';

export default function ChangePasswordModal({
  isOpen,
  onClose,
}: ChangePasswordModalProps) {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [newPasswordValidation, setNewPasswordValidation] =
    useState<ValidationState>('default');
  const [confirmPasswordValidation, setConfirmPasswordValidation] =
    useState<ValidationState>('default');
  const [error, setError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const updateUserMutator = useUpdateUser({
    onSuccess: () => {
      handleClose();
      // Could add a success toast here
    },
    onError: (error) => {
      setError(error?.response?.data?.detail || 'Failed to change password');
      setIsSubmitting(false);
    },
  });

  const handleClose = () => {
    setNewPassword('');
    setConfirmPassword('');
    setNewPasswordValidation('default');
    setConfirmPasswordValidation('default');
    setError('');
    setIsSubmitting(false);
    onClose();
  };

  const validatePassword = (password: string) => {
    if (password.length === 0) {
      return 'default';
    }
    if (password.length < 8) {
      return 'error';
    }
    return 'success';
  };

  const validateConfirmPassword = (confirm: string, original: string) => {
    if (confirm.length === 0) {
      return 'default';
    }
    if (confirm !== original) {
      return 'error';
    }
    return 'success';
  };

  const handleNewPasswordChange = (value: string) => {
    setNewPassword(value);
    setNewPasswordValidation(validatePassword(value));

    // Re-validate confirm password if it exists
    if (confirmPassword.length > 0) {
      setConfirmPasswordValidation(
        validateConfirmPassword(confirmPassword, value),
      );
    }
  };

  const handleConfirmPasswordChange = (value: string) => {
    setConfirmPassword(value);
    setConfirmPasswordValidation(validateConfirmPassword(value, newPassword));
  };

  const canSubmit =
    newPassword.length >= 8 &&
    confirmPassword.length >= 8 &&
    newPassword === confirmPassword &&
    !isSubmitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;

    setIsSubmitting(true);
    setError('');

    try {
      await updateUserMutator.updateUser({
        password: newPassword,
      });
    } catch (error) {
      // Error handling is done through the onError callback
    }
  };

  return (
    <Modal
      variant={ModalVariant.small}
      title="Change Password"
      isOpen={isOpen}
      onClose={handleClose}
      data-testid="change-password-modal"
      actions={[
        <Button
          key="change"
          variant="primary"
          onClick={handleSubmit}
          isDisabled={!canSubmit}
          isLoading={isSubmitting}
          data-testid="change-password-submit"
        >
          Change Password
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>,
      ]}
    >
      <Form>
        <p>
          Enter a new password. Passwords must be at least 8 characters long.
        </p>

        {error && (
          <Alert
            variant="danger"
            isInline
            title="Error"
            className="pf-v5-u-mb-md"
          >
            {error}
          </Alert>
        )}

        <FormGroup fieldId="new-password">
          <TextInput
            id="new-password"
            type="password"
            value={newPassword}
            onChange={(_event, value) => handleNewPasswordChange(value)}
            validated={newPasswordValidation}
            placeholder="Your new password"
          />
          <FormHelperText>
            <HelperText>
              <HelperTextItem
                variant={
                  newPasswordValidation === 'error' ? 'error' : 'default'
                }
              >
                {newPasswordValidation === 'error' && newPassword.length > 0
                  ? 'Password must be at least 8 characters long'
                  : 'Enter your new password'}
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        </FormGroup>

        <FormGroup fieldId="confirm-password">
          <TextInput
            id="confirm-password"
            type="password"
            value={confirmPassword}
            onChange={(_event, value) => handleConfirmPasswordChange(value)}
            validated={confirmPasswordValidation}
            placeholder="Verify your new password"
          />
          <FormHelperText>
            <HelperText>
              <HelperTextItem
                variant={
                  confirmPasswordValidation === 'error' ? 'error' : 'default'
                }
              >
                {confirmPasswordValidation === 'error' &&
                confirmPassword.length > 0
                  ? 'Passwords must match'
                  : 'Re-enter your new password'}
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        </FormGroup>
      </Form>
    </Modal>
  );
}
