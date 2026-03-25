import React from 'react';
import {
  Button,
  ClipboardCopy,
  Content,
  ContentVariants,
  Stack,
  StackItem,
  Alert,
  Modal,
  ModalVariant,
  ModalHeader,
  ModalBody,
  ModalFooter,
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
      isOpen={props.isOpen}
      onClose={props.onClose}
    >
      <ModalHeader title="Access Token Generated" />
      <ModalBody>
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
            <Content component={ContentVariants.p}>
              The access token for <strong>{props.applicationName}</strong> has
              been created with the following permissions:
            </Content>
          </StackItem>

          <StackItem>
            <Stack hasGutter>
              {props.scopes.map((scope) => (
                <StackItem key={scope}>
                  <Content component={ContentVariants.small}>• {scope}</Content>
                </StackItem>
              ))}
            </Stack>
          </StackItem>

          <StackItem>
            <Content component={ContentVariants.h6}>Your Access Token:</Content>
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
              <Content component={ContentVariants.p}>
                Keep this token secure and do not share it. This token provides
                access to your account with the selected permissions. You can
                revoke this token at any time from the OAuth Applications
                settings.
              </Content>
            </Alert>
          </StackItem>
        </Stack>
      </ModalBody>
      <ModalFooter>
        <Button key="close" variant="primary" onClick={props.onClose}>
          Done
        </Button>
      </ModalFooter>
    </Modal>
  );
}
