import React, {useState} from 'react';
import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  TextInput,
  Text,
  Alert,
} from '@patternfly/react-core';

interface FreshLoginModalProps {
  isOpen: boolean;
  onVerify: (password: string) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
  error?: string;
}

export function FreshLoginModal({
  isOpen,
  onVerify,
  onCancel,
  isLoading = false,
  error,
}: FreshLoginModalProps) {
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) return;

    try {
      await onVerify(password);
      setPassword(''); // Clear password on success
    } catch (err) {
      // Error handling is done by parent component
    }
  };

  const handleCancel = () => {
    setPassword('');
    onCancel();
  };

  return (
    <Modal
      variant={ModalVariant.small}
      title="Please Verify"
      isOpen={isOpen}
      onClose={handleCancel}
      actions={[
        <Button
          key="verify"
          variant="primary"
          onClick={handleSubmit}
          isLoading={isLoading}
          isDisabled={!password.trim() || isLoading}
        >
          Verify
        </Button>,
        <Button key="cancel" variant="link" onClick={handleCancel}>
          Cancel
        </Button>,
      ]}
    >
      <Text style={{marginBottom: '1rem'}}>
        It has been more than a few minutes since you last logged in, so please
        verify your password to perform this sensitive operation:
      </Text>

      {error && (
        <Alert variant="danger" title="Verification failed" isInline>
          {error}
        </Alert>
      )}

      <Form onSubmit={handleSubmit}>
        <FormGroup label="Current Password" fieldId="fresh-password" isRequired>
          <TextInput
            id="fresh-password"
            type="password"
            value={password}
            onChange={(_event, value) => setPassword(value)}
            placeholder="Current Password"
            autoFocus
            isDisabled={isLoading}
          />
        </FormGroup>
      </Form>
    </Modal>
  );
}
