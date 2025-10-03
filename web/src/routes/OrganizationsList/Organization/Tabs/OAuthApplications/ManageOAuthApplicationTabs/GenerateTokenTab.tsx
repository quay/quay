import React, {useState} from 'react';
import {
  Button,
  Flex,
  FlexItem,
  HelperText,
  HelperTextItem,
  PageSection,
  PageSectionVariants,
  Stack,
  StackItem,
  Text,
} from '@patternfly/react-core';
import {InfoCircleIcon} from '@patternfly/react-icons';
import {useForm} from 'react-hook-form';
import {IOAuthApplication} from 'src/hooks/UseOAuthApplications';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {FormCheckbox} from 'src/components/forms/FormCheckbox';
import GenerateTokenAuthorizationModal from 'src/components/modals/GenerateTokenAuthorizationModal';
import EntitySearch from 'src/components/EntitySearch';
import {Entity} from 'src/resources/UserResource';
import {GlobalAuthState} from 'src/resources/AuthResource';
import {OAUTH_SCOPES, OAuthScope} from '../types';

interface GenerateTokenTabProps {
  application: IOAuthApplication | null;
  orgName: string;
}

interface GenerateTokenFormData {
  [key: string]: boolean;
}

export default function GenerateTokenTab(props: GenerateTokenTabProps) {
  const [customUser, setCustomUser] = useState(false);
  const [selectedUser, setSelectedUser] = useState<Entity | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const {user} = useCurrentUser();
  const quayConfig = useQuayConfig();

  // Initialize form with all scopes set to false
  const defaultValues: GenerateTokenFormData = {};
  Object.keys(OAUTH_SCOPES).forEach((scope) => {
    defaultValues[scope] = false;
  });

  const {control, watch} = useForm<GenerateTokenFormData>({
    defaultValues,
  });

  const watchedValues = watch();

  if (!props.application) {
    return <Text>No application selected</Text>;
  }

  const application = props.application;

  const getSelectedScopesList = (): string[] => {
    return Object.keys(watchedValues).filter((scope) => watchedValues[scope]);
  };

  const getUrl = (path: string): string => {
    const scheme =
      quayConfig?.config?.PREFERRED_URL_SCHEME ||
      window.location.protocol.replace(':', '');
    const hostname =
      quayConfig?.config?.SERVER_HOSTNAME || window.location.host;
    return `${scheme}://${hostname}${path}`;
  };

  const generateUrl = (): string => {
    if (!application || !quayConfig?.config) return '';

    const scopesString = getSelectedScopesList().join(' ');

    if (selectedUser !== null) {
      const params = new URLSearchParams({
        username: selectedUser.name,
        response_type: 'token',
        client_id: application.client_id,
        scope: scopesString,
        redirect_uri: getUrl(
          quayConfig.config.LOCAL_OAUTH_HANDLER || '/oauth/localapp',
        ),
      });
      return getUrl(`/oauth/authorize/assignuser?${params.toString()}`);
    } else {
      // For generation, use existing format
      const params = new URLSearchParams({
        response_type: 'token',
        client_id: application.client_id,
        scope: scopesString,
        redirect_uri: getUrl(
          quayConfig.config.LOCAL_OAUTH_HANDLER || '/oauth/localapp',
        ),
      });
      return getUrl(`/oauth/authorizeapp?${params.toString()}`);
    }
  };

  const handleGenerateToken = () => {
    if (getSelectedScopesList().length === 0) return;
    setIsAuthModalOpen(true);
  };

  const assignUser = () => {
    setCustomUser(true);
  };

  const cancelAssignUser = () => {
    setSelectedUser(null);
    setCustomUser(false);
  };

  const handleUserSelected = (entity: Entity) => {
    setSelectedUser(entity);
  };

  const handleUserSearchError = () => {
    // Handle search error if needed
    console.error('Error searching for users');
  };

  const handleUserSearchClear = () => {
    setSelectedUser(null);
  };

  const handleAuthModalConfirm = () => {
    // Use POST form submission for both assignment and generation
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = generateUrl();
    form.target = '_blank';
    form.style.display = 'none';

    // Extract URL parameters and add them as form fields
    const url = new URL(generateUrl());
    url.searchParams.forEach((value, key) => {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = key;
      input.value = value;
      form.appendChild(input);
    });

    // Add CSRF token for POST request
    if (GlobalAuthState.csrfToken) {
      const csrfInput = document.createElement('input');
      csrfInput.type = 'hidden';
      csrfInput.name = '_csrf_token';
      csrfInput.value = GlobalAuthState.csrfToken;
      form.appendChild(csrfInput);
    }

    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);

    setIsAuthModalOpen(false);
  };

  const handleAuthModalClose = () => {
    setIsAuthModalOpen(false);
  };

  return (
    <PageSection variant={PageSectionVariants.light}>
      <Stack hasGutter>
        <HelperText>
          <HelperTextItem>
            <Text>
              Click the button below to generate a new{' '}
              <Button
                variant="link"
                isInline
                component="a"
                href="http://tools.ietf.org/html/rfc6749#section-1.4"
                target="_blank"
                rel="noopener noreferrer"
              >
                OAuth 2 Access Token
              </Button>
              . Note tokens are used for authentication only.{' '}
              <InfoCircleIcon
                style={{
                  marginLeft: 'var(--pf-global--spacer--lg)',
                  color: 'var(--pf-global--info-color--100)',
                }}
                title="The token is used for authentication only and not authorization. While the token scope permits authentication to the API, additional permissions may be required for authorization. e.g. A token with the create repository scope will not permit creation of a repository without the user being granted the Create Repository team permission."
              />
            </Text>
            <Flex
              spaceItems={{default: 'spaceItemsSm'}}
              alignItems={{default: 'alignItemsCenter'}}
            >
              <FlexItem>
                <Text>
                  The generated token will act on behalf of user{' '}
                  {!customUser && <strong>{user?.username || 'user'}</strong>}
                </Text>
              </FlexItem>
              {customUser && (
                <FlexItem>
                  <EntitySearch
                    org={props.orgName}
                    includeTeams={false}
                    includeRobots={false}
                    placeholderText="User"
                    onSelect={handleUserSelected}
                    onError={handleUserSearchError}
                    onClear={handleUserSearchClear}
                    value={selectedUser?.name}
                  />
                </FlexItem>
              )}
              <FlexItem>
                {!customUser ? (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={assignUser}
                    data-testid="assign-user-button"
                  >
                    Assign another user
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={cancelAssignUser}
                    data-testid="cancel-assign-button"
                  >
                    Cancel
                  </Button>
                )}
              </FlexItem>
            </Flex>
          </HelperTextItem>
        </HelperText>
        <StackItem>
          <Stack hasGutter>
            {Object.entries(OAUTH_SCOPES).map(
              ([scopeName, scopeInfo]: [string, OAuthScope]) => (
                <StackItem key={scopeName}>
                  <FormCheckbox
                    name={scopeName}
                    control={control}
                    label={scopeInfo.title}
                    description={scopeInfo.description}
                    data-testid={`scope-${scopeName}`}
                  />
                </StackItem>
              ),
            )}
          </Stack>
        </StackItem>
        <StackItem>
          {!customUser ? (
            <Button
              variant="primary"
              onClick={handleGenerateToken}
              isDisabled={getSelectedScopesList().length === 0}
              data-testid="generate-token-button"
            >
              Generate Access Token
            </Button>
          ) : (
            <Button
              variant="primary"
              onClick={handleGenerateToken}
              isDisabled={!selectedUser || getSelectedScopesList().length === 0}
              data-testid="generate-token-button"
            >
              Assign token
            </Button>
          )}
        </StackItem>
      </Stack>

      {props.application && (
        <GenerateTokenAuthorizationModal
          isOpen={isAuthModalOpen}
          onClose={handleAuthModalClose}
          onConfirm={handleAuthModalConfirm}
          application={props.application}
          selectedScopes={getSelectedScopesList()}
          scopesData={OAUTH_SCOPES}
          hasDangerousScopes={getSelectedScopesList().some(
            (scope) => OAUTH_SCOPES[scope]?.dangerous,
          )}
          isAssignmentMode={customUser && selectedUser !== null}
          targetUsername={selectedUser?.name}
        />
      )}
    </PageSection>
  );
}
