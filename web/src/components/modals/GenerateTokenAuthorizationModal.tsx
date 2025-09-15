import React, {useState} from 'react';
import {
  Button,
  Alert,
  Modal,
  ModalVariant,
  Text,
  TextVariants,
  Stack,
  StackItem,
} from '@patternfly/react-core';
import {
  ExclamationTriangleIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from '@patternfly/react-icons';
import {IOAuthApplication} from 'src/hooks/UseOAuthApplications';

// OAuth scope interface - we'll get this from the JSON endpoint
interface OAuthScope {
  title: string;
  description: string;
  dangerous?: boolean;
}

interface GenerateTokenAuthorizationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  application: IOAuthApplication;
  selectedScopes: string[];
  scopesData: Record<string, OAuthScope>;
  hasDangerousScopes?: boolean;
  isAssignmentMode?: boolean;
  targetUsername?: string;
}

export default function GenerateTokenAuthorizationModal(
  props: GenerateTokenAuthorizationModalProps,
) {
  const [expandedScopes, setExpandedScopes] = useState<Set<string>>(new Set());

  const toggleScope = (scopeName: string) => {
    setExpandedScopes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(scopeName)) {
        newSet.delete(scopeName);
      } else {
        newSet.add(scopeName);
      }
      return newSet;
    });
  };

  const isAssignment = props.isAssignmentMode && props.targetUsername;

  return (
    <Modal
      variant={ModalVariant.medium}
      title={isAssignment ? 'Assign Authorization?' : props.application.name}
      isOpen={props.isOpen}
      onClose={props.onClose}
      actions={[
        <Button key="authorize" variant="primary" onClick={props.onConfirm}>
          {isAssignment ? 'Assign token' : 'Authorize Application'}
        </Button>,
        <Button key="cancel" variant="link" onClick={props.onClose}>
          Cancel
        </Button>,
      ]}
    >
      <Stack hasGutter>
        {props.hasDangerousScopes && (
          <StackItem>
            <Alert
              variant="warning"
              title={
                isAssignment
                  ? `Dangerous scopes will be granted to ${props.targetUsername}. Please ensure the scopes and the user are correct.`
                  : 'This scope grants permissions which are potentially dangerous. Be careful when authorizing it!'
              }
              isInline
            />
          </StackItem>
        )}
        <StackItem>
          <Text component={TextVariants.p}>
            {isAssignment
              ? `This will prompt user ${props.targetUsername} to generate a token with the following permissions:`
              : 'This application would like permission to:'}
          </Text>
        </StackItem>
        <StackItem>
          <Stack hasGutter>
            {props.selectedScopes.map((scopeName) => {
              const scopeInfo = props.scopesData[scopeName];
              const isDangerous = scopeInfo?.dangerous;
              const isExpanded = expandedScopes.has(scopeName);

              return (
                <StackItem key={scopeName}>
                  <div>
                    <Button
                      variant="link"
                      isInline
                      onClick={() => toggleScope(scopeName)}
                      icon={
                        isExpanded ? <ChevronDownIcon /> : <ChevronRightIcon />
                      }
                      iconPosition="left"
                      style={{
                        padding: 0,
                        fontSize: 'inherit',
                        textAlign: 'left',
                      }}
                    >
                      <strong>{scopeInfo?.title}</strong>
                      {isDangerous && (
                        <ExclamationTriangleIcon
                          style={{
                            color: '#f0ab00',
                            marginLeft: '8px',
                            display: 'inline-block',
                          }}
                        />
                      )}
                    </Button>

                    {isExpanded && (
                      <div
                        style={{
                          marginLeft: 'var(--pf-global--spacer--lg)',
                          marginTop: 'var(--pf-global--spacer--xs)',
                          paddingLeft: 'var(--pf-global--spacer--sm)',
                        }}
                      >
                        <Text component={TextVariants.small}>
                          {scopeInfo?.description}
                        </Text>
                      </div>
                    )}
                  </div>
                </StackItem>
              );
            })}
          </Stack>
        </StackItem>
      </Stack>
    </Modal>
  );
}
