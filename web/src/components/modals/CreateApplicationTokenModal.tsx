import React, {useState} from 'react';
import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  TextInput,
  Alert,
  Text,
  ClipboardCopy,
} from '@patternfly/react-core';
import {useCreateApplicationToken} from 'src/hooks/UseApplicationTokens';
import {IApplicationToken} from 'src/resources/UserResource';

interface CreateApplicationTokenModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CreateApplicationTokenModal({
  isOpen,
  onClose,
}: CreateApplicationTokenModalProps) {
  const [title, setTitle] = useState('');
  const [createdToken, setCreatedToken] = useState<IApplicationToken | null>(
    null,
  );
  const [error, setError] = useState('');

  const createTokenMutator = useCreateApplicationToken({
    onSuccess: (data) => {
      setCreatedToken(data.token);
      setError('');
    },
    onError: (err) => {
      setError(err.message);
    },
  });

  const handleClose = () => {
    setTitle('');
    setCreatedToken(null);
    setError('');
    onClose();
  };

  const handleCreate = async () => {
    if (!title.trim()) {
      setError('Token title is required');
      return;
    }

    setError('');
    try {
      await createTokenMutator.mutateAsync(title.trim());
    } catch (error) {
      // Error handling is done in the onError callback
    }
  };

  const canCreate = title.trim().length > 0 && !createTokenMutator.isLoading;

  // If token was created successfully, show the token
  if (createdToken) {
    return (
      <Modal
        variant={ModalVariant.medium}
        title="Application Token Created"
        isOpen={isOpen}
        onClose={handleClose}
        data-testid="create-token-modal"
        actions={[
          <Button
            key="done"
            variant="primary"
            onClick={handleClose}
            data-testid="create-token-close"
          >
            Done
          </Button>,
        ]}
      >
        <Alert
          variant="success"
          isInline
          title="Token Created Successfully"
          className="pf-v5-u-mb-md"
        >
          Your application token has been created and can be used in place of
          your password for Docker and other CLI commands. Make sure to copy and
          save it securely - you will not be able to see it again.
        </Alert>

        <Form>
          <FormGroup label="Token Name" fieldId="token-name">
            <Text>{createdToken.title}</Text>
          </FormGroup>

          <FormGroup label="Token" fieldId="token-code">
            <ClipboardCopy
              hoverTip="Copy"
              clickTip="Copied"
              variant="expansion"
              isReadOnly
              data-testid="copy-token-button"
            >
              {createdToken.token_code}
            </ClipboardCopy>
          </FormGroup>
        </Form>
      </Modal>
    );
  }

  // Otherwise show the creation form
  return (
    <Modal
      variant={ModalVariant.small}
      title="Create Application Token"
      isOpen={isOpen}
      onClose={handleClose}
      data-testid="create-token-modal"
      actions={[
        <Button
          key="create"
          variant="primary"
          onClick={handleCreate}
          isDisabled={!canCreate}
          isLoading={createTokenMutator.isLoading}
          data-testid="create-token-submit"
        >
          Create Token
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>,
      ]}
    >
      <Form>
        <Text className="pf-v5-u-mb-md">
          Create an application token that can be used in place of your password
          for Docker and other CLI authentication.
        </Text>

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

        <FormGroup label="Token Name" fieldId="token-title" isRequired>
          <TextInput
            id="token-title"
            type="text"
            value={title}
            onChange={(_event, value) => setTitle(value)}
            placeholder="Enter a name for this token"
            isRequired
          />
        </FormGroup>
      </Form>
    </Modal>
  );
}
