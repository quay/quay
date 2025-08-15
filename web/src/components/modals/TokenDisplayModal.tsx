import React from 'react';
import {
  Button,
  ClipboardCopy,
  Modal,
  ModalVariant,
  Text,
  TextVariants,
  Stack,
  StackItem,
  Alert,
} from '@patternfly/react-core';
import {CheckCircleIcon} from '@patternfly/react-icons';

interface TokenDisplayModalProps {
  isOpen: boolean;
  onClose: () => void;
  token: string;
  applicationName: string;
  scopes: string[];
}

export default function TokenDisplayModal(props: TokenDisplayModalProps) {
  return (
    <Modal
      variant={ModalVariant.medium}
      title="Access Token Generated"
      isOpen={props.isOpen}
      onClose={props.onClose}
      actions={[
        <Button key="close" variant="primary" onClick={props.onClose}>
          Done
        </Button>,
      ]}
    >
      <Stack hasGutter>
        <StackItem>
          <Alert
            variant="success"
            title="Your access token has been successfully generated!"
            isInline
            customIcon={<CheckCircleIcon />}
          />
        </StackItem>

        <StackItem>
          <Text component={TextVariants.p}>
            The access token for <strong>{props.applicationName}</strong> has
            been created with the following permissions:
          </Text>
        </StackItem>

        <StackItem>
          <Stack hasGutter>
            {props.scopes.map((scope) => (
              <StackItem key={scope}>
                <Text component={TextVariants.small}>• {scope}</Text>
              </StackItem>
            ))}
          </Stack>
        </StackItem>

        <StackItem>
          <Text component={TextVariants.h6}>Your Access Token:</Text>
        </StackItem>

        <StackItem>
          <ClipboardCopy
            isReadOnly
            hoverTip="Copy to clipboard"
            clickTip="Copied!"
            variant="expansion"
          >
            {props.token}
          </ClipboardCopy>
        </StackItem>

        <StackItem>
          <Alert variant="warning" title="Important Security Notice" isInline>
            <Text component={TextVariants.p}>
              Keep this token secure and do not share it. This token provides
              access to your account with the selected permissions. You can
              revoke this token at any time from the OAuth Applications
              settings.
            </Text>
          </Alert>
        </StackItem>
      </Stack>
    </Modal>
  );
}
