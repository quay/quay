import React, {useRef, useState} from 'react';
import {
  Alert,
  Button,
  Checkbox,
  Content,
  Dropdown,
  DropdownItem,
  DropdownList,
  Form,
  FormGroup,
  FormSelect,
  FormSelectOption,
  MenuToggle,
  MenuToggleElement,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  ModalVariant,
  PageSection,
  Stack,
  StackItem,
  TextInput,
  Toolbar,
  ToolbarContent,
  ToolbarItem,
} from '@patternfly/react-core';
import {KeyIcon} from '@patternfly/react-icons';
import EllipsisVIcon from '@patternfly/react-icons/dist/esm/icons/ellipsis-v-icon';
import {
  Table,
  TableText,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from '@patternfly/react-table';
import Empty from 'src/components/empty/Empty';
import EntitySearch from 'src/components/EntitySearch';
import ErrorBoundary from 'src/components/errors/ErrorBoundary';
import RequestError from 'src/components/errors/RequestError';
import {SuspenseLoader} from 'src/components/SuspenseLoader';
import GenerateTokenAuthorizationModal from 'src/components/modals/GenerateTokenAuthorizationModal';
import TokenDisplayModal from 'src/components/modals/TokenDisplayModal';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {
  useAssignOAuthApplicationTokenToUser,
  useCreateOAuthApplicationToken,
  useFetchOAuthApplicationTokens,
  useRevokeOAuthApplicationToken,
} from 'src/hooks/UseOAuthApplications';
import type {
  IOAuthApplication,
  IOAuthApplicationToken,
} from 'src/resources/OAuthApplicationTypes';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {formatDate} from 'src/libs/utils';
import type {Entity} from 'src/resources/UserResource';
import {OAUTH_SCOPES} from '../types';
import type {OAuthScope} from '../types';

interface APIAccessTokensTabProps {
  application: IOAuthApplication | null;
  orgName: string;
}

const SECONDS_PER_DAY = 60 * 60 * 24;
const DEFAULT_EXPIRATION_ID = '10-years';
const EXPIRATION_OPTIONS = [
  {id: '7-days', label: '7 days', seconds: 7 * SECONDS_PER_DAY},
  {id: '30-days', label: '30 days', seconds: 30 * SECONDS_PER_DAY},
  {id: '90-days', label: '90 days', seconds: 90 * SECONDS_PER_DAY},
  {id: '1-year', label: '1 year', seconds: 365 * SECONDS_PER_DAY},
  {
    id: DEFAULT_EXPIRATION_ID,
    label: '10 years',
    seconds: Math.floor(365.25 * 10 * SECONDS_PER_DAY),
  },
];

type ExpirationOption = (typeof EXPIRATION_OPTIONS)[number];

function getExpirationOption(expirationId: string): ExpirationOption {
  return (
    EXPIRATION_OPTIONS.find((option) => option.id === expirationId) ||
    EXPIRATION_OPTIONS[EXPIRATION_OPTIONS.length - 1]
  );
}

function formatTokenName(token: IOAuthApplicationToken): string {
  return token.name || '';
}

function formatTokenReference(token: IOAuthApplicationToken): string {
  return token.name || token.uuid;
}

function formatCreatedBy(token: IOAuthApplicationToken): string {
  return token.created_by || 'Unknown';
}

function getScopeNames(scope: string): string[] {
  return scope.trim().split(/\s+/).filter(Boolean);
}

function formatCreated(created: string | null): string {
  return created ? formatDate(created) : 'Unknown';
}

function formatExpires(expiresAt: string | null): string {
  return expiresAt ? formatDate(expiresAt) : 'Never';
}

function formatLastUsed(lastAccessed: string | null): string {
  return lastAccessed ? formatDate(lastAccessed) : 'Never';
}

function getOAuthRedirectUri(localOAuthHandler?: string): string {
  const redirectUri = localOAuthHandler || '/oauth/localapp';
  return redirectUri.startsWith('http')
    ? redirectUri
    : `${window.location.origin}${redirectUri}`;
}

function getSelectedScopeTitles(selectedScopes: string[]): string[] {
  return selectedScopes.map((scope) => OAUTH_SCOPES[scope]?.title || scope);
}

function hasDangerousScopes(selectedScopes: string[]): boolean {
  return selectedScopes.some((scope) => OAUTH_SCOPES[scope]?.dangerous);
}

const ScopeSummary: React.FC<{scope: string}> = ({
  scope,
}): React.ReactElement => {
  const scopes = getScopeNames(scope);

  if (scopes.length === 0) {
    return <TableText>No scopes</TableText>;
  }

  return (
    <span
      style={{
        overflowWrap: 'break-word',
        whiteSpace: 'normal',
      }}
      data-testid="api-token-scopes-summary"
    >
      {scopes.join(', ')}
    </span>
  );
};

interface TokenActionsProps {
  token: IOAuthApplicationToken;
  onRevoke: () => void;
}

const TokenActions: React.FC<TokenActionsProps> = ({
  token,
  onRevoke,
}): React.ReactElement => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Dropdown
      isOpen={isOpen}
      onOpenChange={setIsOpen}
      onSelect={() => setIsOpen(false)}
      toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
          ref={toggleRef}
          variant="plain"
          aria-label={`Actions for ${formatTokenReference(token)}`}
          onClick={() => setIsOpen((previousIsOpen) => !previousIsOpen)}
          isExpanded={isOpen}
          data-testid={`api-token-actions-${token.uuid}`}
        >
          <EllipsisVIcon />
        </MenuToggle>
      )}
      shouldFocusToggleOnSelect
      popperProps={{enableFlip: true, position: 'right'}}
    >
      <DropdownList>
        <DropdownItem
          key="revoke"
          onClick={onRevoke}
          className="red-color"
          data-testid={`revoke-api-token-${token.uuid}`}
        >
          Revoke
        </DropdownItem>
      </DropdownList>
    </Dropdown>
  );
};

interface TokenInventoryProps {
  orgName: string;
  clientId: string;
  canManage: boolean;
  onGenerate: () => void;
  onRevoke: (token: IOAuthApplicationToken) => void;
}

const TokenInventory: React.FC<TokenInventoryProps> = ({
  orgName,
  clientId,
  canManage,
  onGenerate,
  onRevoke,
}): React.ReactElement => {
  const {tokens, errorRefreshingOAuthApplicationTokens} =
    useFetchOAuthApplicationTokens(orgName, clientId);

  return (
    <PageSection hasBodyWrapper={false}>
      {errorRefreshingOAuthApplicationTokens && (
        <Alert
          variant="danger"
          isInline
          title="Unable to refresh API access tokens. Displayed token data may be out of date."
          data-testid="api-access-tokens-refresh-error"
        />
      )}
      {canManage && (
        <Toolbar>
          <ToolbarContent>
            <ToolbarItem>
              <Button
                variant="primary"
                onClick={onGenerate}
                data-testid="generate-new-api-token-button"
              >
                Generate New Token
              </Button>
            </ToolbarItem>
          </ToolbarContent>
        </Toolbar>
      )}
      {tokens.length === 0 ? (
        <Empty
          title="No API access tokens"
          icon={KeyIcon}
          body="This OAuth application does not have any API access tokens."
        />
      ) : (
        <Table
          aria-label="API Access Tokens table"
          data-testid="api-access-tokens-table"
          variant="compact"
        >
          <Thead>
            <Tr>
              <Th modifier="nowrap">Name</Th>
              <Th modifier="nowrap" style={{minWidth: '7rem'}}>
                Created By
              </Th>
              <Th modifier="nowrap" width={30}>
                Scopes
              </Th>
              <Th modifier="nowrap">Created</Th>
              <Th modifier="nowrap">Expires</Th>
              <Th modifier="nowrap">Last Used</Th>
              {canManage && <Th modifier="nowrap" screenReaderText="Actions" />}
            </Tr>
          </Thead>
          <Tbody>
            {tokens.map((token) => (
              <Tr key={token.uuid}>
                <Td dataLabel="Name">{formatTokenName(token)}</Td>
                <Td dataLabel="Created By" modifier="nowrap">
                  {formatCreatedBy(token)}
                </Td>
                <Td
                  dataLabel="Scopes"
                  modifier="wrap"
                  style={{maxWidth: '36rem'}}
                >
                  <ScopeSummary scope={token.scope} />
                </Td>
                <Td dataLabel="Created">{formatCreated(token.created)}</Td>
                <Td dataLabel="Expires">{formatExpires(token.expires_at)}</Td>
                <Td dataLabel="Last Used">
                  {formatLastUsed(token.last_accessed)}
                </Td>
                {canManage && (
                  <Td dataLabel="Actions">
                    <TokenActions
                      token={token}
                      onRevoke={() => onRevoke(token)}
                    />
                  </Td>
                )}
              </Tr>
            ))}
          </Tbody>
        </Table>
      )}
    </PageSection>
  );
};

const APIAccessTokensTab: React.FC<APIAccessTokensTabProps> = (
  props,
): React.ReactElement => {
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState(false);
  const [isAuthorizationModalOpen, setIsAuthorizationModalOpen] =
    useState(false);
  const [tokenName, setTokenName] = useState('');
  const [expirationId, setExpirationId] = useState(DEFAULT_EXPIRATION_ID);
  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
  const [customUser, setCustomUser] = useState(false);
  const [selectedUser, setSelectedUser] = useState<Entity | null>(null);
  const [generateError, setGenerateError] = useState('');
  const [generatedToken, setGeneratedToken] =
    useState<IOAuthApplicationToken | null>(null);
  const [generatedScopes, setGeneratedScopes] = useState<string[]>([]);
  const [isTokenDisplayModalOpen, setIsTokenDisplayModalOpen] = useState(false);
  const [tokenToRevoke, setTokenToRevoke] =
    useState<IOAuthApplicationToken | null>(null);
  const [revokeError, setRevokeError] = useState('');
  const authorizationRequestInFlight = useRef(false);
  const revokeRequestInFlight = useRef(false);
  const {user} = useCurrentUser();
  const quayConfig = useQuayConfig();
  const {addAlert} = useUI();

  const clientId = props.application?.client_id || '';
  const assignOAuthTokenEnabled =
    quayConfig?.features?.ASSIGN_OAUTH_TOKEN === true;
  const canManage =
    user != null &&
    quayConfig != null &&
    user.global_readonly_super_user !== true &&
    quayConfig.registry_state !== 'readonly';
  const localOAuthHandler = quayConfig?.config?.LOCAL_OAUTH_HANDLER;

  const resetAssignment = (): void => {
    setCustomUser(false);
    setSelectedUser(null);
  };

  const resetTokenForm = (): void => {
    resetAssignment();
    setTokenName('');
    setExpirationId(DEFAULT_EXPIRATION_ID);
    setSelectedScopes([]);
    setGenerateError('');
  };

  const {
    createOAuthApplicationTokenMutationAsync,
    creatingOAuthApplicationToken,
  } = useCreateOAuthApplicationToken(
    props.orgName,
    clientId,
    (createdToken) => {
      setGeneratedToken(createdToken);
      setGeneratedScopes(
        getSelectedScopeTitles(getScopeNames(createdToken.scope)),
      );
      setIsTokenDisplayModalOpen(true);
      setIsGenerateModalOpen(false);
      setIsAuthorizationModalOpen(false);
      resetTokenForm();
    },
    () => {
      setGenerateError(
        'Unable to generate API access token. Please try again.',
      );
    },
  );

  const {
    assignOAuthApplicationTokenToUserMutationAsync,
    assigningOAuthApplicationTokenToUser,
  } = useAssignOAuthApplicationTokenToUser(
    clientId,
    (response) => {
      addAlert({
        variant: AlertVariant.Success,
        title: response.message || 'Token assigned successfully',
      });
      setIsGenerateModalOpen(false);
      setIsAuthorizationModalOpen(false);
      resetTokenForm();
    },
    () => {
      setGenerateError('Unable to assign API access token. Please try again.');
    },
  );

  const {
    revokeOAuthApplicationTokenMutationAsync,
    revokingOAuthApplicationToken,
  } = useRevokeOAuthApplicationToken(
    props.orgName,
    clientId,
    () => {
      setTokenToRevoke(null);
      setRevokeError('');
    },
    () => {
      setRevokeError('Unable to revoke API access token. Please try again.');
    },
  );

  if (!props.application) {
    return <Content component="p">No application selected</Content>;
  }

  const toggleScope = (scopeName: string, isChecked: boolean): void => {
    setSelectedScopes((prevSelectedScopes) => {
      const otherScopes = prevSelectedScopes.filter(
        (scope) => scope !== scopeName,
      );
      return isChecked ? [...otherScopes, scopeName] : otherScopes;
    });
  };

  const expirationOption = getExpirationOption(expirationId);
  const isAssignmentMode = customUser && selectedUser !== null;
  const authorizationRequestPending =
    creatingOAuthApplicationToken || assigningOAuthApplicationTokenToUser;
  const canGenerate =
    canManage &&
    (customUser || tokenName.trim().length > 0) &&
    selectedScopes.length > 0 &&
    (!customUser || selectedUser !== null) &&
    !authorizationRequestPending;

  const handleOpenAuthorizationConfirmation = (): void => {
    if (!canGenerate) return;

    setGenerateError('');
    setIsGenerateModalOpen(false);
    setIsAuthorizationModalOpen(true);
  };

  const handleAuthorizationModalClose = (): void => {
    if (authorizationRequestInFlight.current || authorizationRequestPending) {
      return;
    }

    setIsAuthorizationModalOpen(false);
    setIsGenerateModalOpen(true);
  };

  const handleGenerateModalClose = (): void => {
    setIsGenerateModalOpen(false);
    resetTokenForm();
  };

  const handleCreateToken = async (): Promise<void> => {
    setGenerateError('');
    try {
      await createOAuthApplicationTokenMutationAsync({
        name: tokenName.trim(),
        scope: selectedScopes.join(' '),
        expiration: expirationOption.seconds,
      });
    } catch {
      setIsAuthorizationModalOpen(false);
      setIsGenerateModalOpen(true);
    }
  };

  const handleAssignToken = async (): Promise<void> => {
    if (!selectedUser) return;

    setGenerateError('');
    try {
      await assignOAuthApplicationTokenToUserMutationAsync({
        username: selectedUser.name,
        scope: selectedScopes.join(' '),
        redirect_uri: getOAuthRedirectUri(localOAuthHandler),
      });
    } catch {
      setIsAuthorizationModalOpen(false);
      setIsGenerateModalOpen(true);
    }
  };

  const handleAuthorizationConfirm = async (): Promise<void> => {
    if (
      !canManage ||
      authorizationRequestInFlight.current ||
      authorizationRequestPending
    ) {
      return;
    }

    authorizationRequestInFlight.current = true;
    try {
      if (isAssignmentMode) {
        await handleAssignToken();
      } else {
        await handleCreateToken();
      }
    } finally {
      authorizationRequestInFlight.current = false;
    }
  };

  const handleRevokeToken = async (): Promise<void> => {
    if (
      !canManage ||
      !tokenToRevoke ||
      revokeRequestInFlight.current ||
      revokingOAuthApplicationToken
    ) {
      return;
    }

    revokeRequestInFlight.current = true;
    setRevokeError('');
    try {
      await revokeOAuthApplicationTokenMutationAsync(tokenToRevoke.uuid);
    } catch {
      // Error state is set by the mutation onError callback.
    } finally {
      revokeRequestInFlight.current = false;
    }
  };

  const handleRevokeModalClose = (): void => {
    if (revokeRequestInFlight.current || revokingOAuthApplicationToken) {
      return;
    }

    setTokenToRevoke(null);
    setRevokeError('');
  };

  const generateTokenModal = (
    <Modal
      variant={ModalVariant.medium}
      isOpen={isGenerateModalOpen}
      onClose={handleGenerateModalClose}
      data-testid="generate-api-token-modal"
    >
      <ModalHeader title="Generate API access token" />
      <ModalBody>
        <Form>
          {generateError && (
            <Alert
              variant="danger"
              isInline
              title={generateError}
              data-testid="generate-api-token-error"
            />
          )}
          {!customUser && (
            <>
              <FormGroup label="Token name" fieldId="api-token-name" isRequired>
                <TextInput
                  id="api-token-name"
                  value={tokenName}
                  onChange={(_event, value) => setTokenName(value)}
                  data-testid="api-token-name-input"
                  isRequired
                />
              </FormGroup>
              <FormGroup
                label="Expiration"
                fieldId="api-token-expiration"
                isRequired
              >
                <FormSelect
                  id="api-token-expiration"
                  aria-label="API token expiration"
                  value={expirationId}
                  onChange={(_event, value) => setExpirationId(value)}
                  data-testid="api-token-expiration-select"
                >
                  {EXPIRATION_OPTIONS.map((option) => (
                    <FormSelectOption
                      key={option.id}
                      value={option.id}
                      label={option.label}
                    />
                  ))}
                </FormSelect>
              </FormGroup>
            </>
          )}
          <FormGroup label="Token owner" fieldId="api-token-owner">
            <Stack hasGutter>
              <StackItem>
                <Content component="p">
                  The token will act on behalf of user{' '}
                  {!customUser && <strong>{user?.username || 'user'}</strong>}
                </Content>
              </StackItem>
              {customUser && (
                <StackItem>
                  <EntitySearch
                    org={props.orgName}
                    includeTeams={false}
                    includeRobots={false}
                    placeholderText="User"
                    onSelect={(entity) => setSelectedUser(entity)}
                    onError={() =>
                      setGenerateError(
                        'Unable to search users. Please try again.',
                      )
                    }
                    onClear={() => setSelectedUser(null)}
                    value={selectedUser?.name}
                  />
                </StackItem>
              )}
              {canManage && assignOAuthTokenEnabled && (
                <StackItem>
                  {!customUser ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setCustomUser(true)}
                      data-testid="assign-user-button"
                    >
                      Assign another user
                    </Button>
                  ) : (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={resetAssignment}
                      data-testid="cancel-assign-button"
                    >
                      Cancel assignment
                    </Button>
                  )}
                </StackItem>
              )}
            </Stack>
          </FormGroup>
          <FormGroup label="Scopes" fieldId="api-token-scopes" isRequired>
            <Stack hasGutter>
              {Object.entries(OAUTH_SCOPES).map(
                ([scopeName, scopeInfo]: [string, OAuthScope]) => (
                  <StackItem key={scopeName}>
                    <Checkbox
                      id={`api-token-scope-${scopeName}`}
                      label={scopeInfo.title}
                      description={scopeInfo.description}
                      isChecked={selectedScopes.includes(scopeName)}
                      onChange={(_event, checked) =>
                        toggleScope(scopeName, checked)
                      }
                      data-testid={`api-token-scope-${scopeName}`}
                    />
                  </StackItem>
                ),
              )}
            </Stack>
          </FormGroup>
        </Form>
      </ModalBody>
      <ModalFooter>
        <Button
          variant="primary"
          onClick={handleOpenAuthorizationConfirmation}
          isDisabled={!canGenerate}
          isLoading={
            creatingOAuthApplicationToken ||
            assigningOAuthApplicationTokenToUser
          }
          data-testid="generate-api-token-submit"
        >
          {customUser ? 'Assign token' : 'Generate token'}
        </Button>
        <Button variant="link" onClick={handleGenerateModalClose}>
          Cancel
        </Button>
      </ModalFooter>
    </Modal>
  );

  const authorizationModal = props.application ? (
    <GenerateTokenAuthorizationModal
      isOpen={isAuthorizationModalOpen}
      onClose={handleAuthorizationModalClose}
      onConfirm={handleAuthorizationConfirm}
      application={props.application}
      selectedScopes={selectedScopes}
      scopesData={OAUTH_SCOPES}
      hasDangerousScopes={hasDangerousScopes(selectedScopes)}
      isAssignmentMode={isAssignmentMode}
      targetUsername={selectedUser?.name}
      isPending={authorizationRequestPending}
    />
  ) : null;

  const revokeTokenModal = (
    <Modal
      variant={ModalVariant.small}
      isOpen={tokenToRevoke !== null}
      onClose={
        revokingOAuthApplicationToken ? undefined : handleRevokeModalClose
      }
      data-testid="revoke-api-token-modal"
    >
      <ModalHeader title="Revoke API access token" />
      <ModalBody>
        <Stack hasGutter>
          {revokeError && (
            <StackItem>
              <Alert
                variant="danger"
                isInline
                title={revokeError}
                data-testid="revoke-api-token-error"
              />
            </StackItem>
          )}
          <StackItem>
            Revoking this token cannot be undone. Applications using token
            &quot;
            <strong>
              {tokenToRevoke ? formatTokenReference(tokenToRevoke) : ''}
            </strong>
            &quot; will no longer be able to authenticate.
          </StackItem>
        </Stack>
      </ModalBody>
      <ModalFooter>
        <Button
          variant="danger"
          onClick={handleRevokeToken}
          isLoading={revokingOAuthApplicationToken}
          isDisabled={revokingOAuthApplicationToken}
          data-testid="revoke-api-token-confirm"
        >
          Revoke token
        </Button>
        <Button
          variant="link"
          onClick={handleRevokeModalClose}
          isDisabled={revokingOAuthApplicationToken}
        >
          Cancel
        </Button>
      </ModalFooter>
    </Modal>
  );

  const tokenDisplayModal = generatedToken?.token ? (
    <TokenDisplayModal
      isOpen={isTokenDisplayModalOpen}
      onClose={() => {
        setIsTokenDisplayModalOpen(false);
        setGeneratedToken(null);
        setGeneratedScopes([]);
      }}
      token={generatedToken.token}
      applicationName={props.application.name}
      scopes={generatedScopes}
    />
  ) : null;

  return (
    <>
      <ErrorBoundary
        key={clientId}
        fallback={<RequestError message="Unable to load API access tokens" />}
      >
        <SuspenseLoader>
          <TokenInventory
            orgName={props.orgName}
            clientId={clientId}
            canManage={canManage}
            onGenerate={() => setIsGenerateModalOpen(true)}
            onRevoke={setTokenToRevoke}
          />
        </SuspenseLoader>
      </ErrorBoundary>
      {canManage && generateTokenModal}
      {canManage && authorizationModal}
      {tokenDisplayModal}
      {canManage && revokeTokenModal}
    </>
  );
};

export default APIAccessTokensTab;
