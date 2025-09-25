import React from 'react';
import {Modal, ModalVariant, Button, Alert, Text} from '@patternfly/react-core';
import {useRevokeApplicationToken} from 'src/hooks/UseApplicationTokens';
import {IApplicationToken} from 'src/resources/UserResource';

interface RevokeTokenModalProps {
  isOpen: boolean;
  onClose: () => void;
  token: IApplicationToken | null;
}

export default function RevokeTokenModal({
  isOpen,
  onClose,
  token,
}: RevokeTokenModalProps) {
  const revokeTokenMutator = useRevokeApplicationToken({
    onSuccess: () => {
      onClose();
    },
    onError: (err) => {
      // Could add error handling here if needed
      console.error('Failed to revoke token:', err);
    },
  });

  const handleRevoke = async () => {
    if (!token?.uuid) return;

    try {
      await revokeTokenMutator.mutateAsync(token.uuid);
    } catch (error) {
      // Error handling is done in the onError callback
    }
  };

  if (!token) return null;

  return (
    <Modal
      variant={ModalVariant.small}
      title="Revoke Application Token"
      isOpen={isOpen}
      onClose={onClose}
      data-testid="revoke-token-modal"
      actions={[
        <Button
          key="revoke"
          variant="danger"
          onClick={handleRevoke}
          isLoading={revokeTokenMutator.isLoading}
          data-testid="revoke-token-confirm"
        >
          Revoke Token
        </Button>,
        <Button key="cancel" variant="link" onClick={onClose}>
          Cancel
        </Button>,
      ]}
    >
      <Alert
        variant="warning"
        isInline
        title="Warning"
        className="pf-v5-u-mb-md"
      >
        This action cannot be undone. Any applications using this token will no
        longer be able to authenticate.
      </Alert>

      <Text>
        Are you sure you want to revoke the application token &quot;
        <strong>{token.title}</strong>&quot;?
      </Text>
    </Modal>
  );
}
