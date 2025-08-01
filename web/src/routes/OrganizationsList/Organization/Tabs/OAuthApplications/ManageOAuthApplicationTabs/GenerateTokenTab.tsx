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
import TokenDisplayModal from 'src/components/modals/TokenDisplayModal';
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
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isTokenModalOpen, setIsTokenModalOpen] = useState(false);
  const [generatedToken, setGeneratedToken] = useState<string>('');
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

    const base =
      selectedUser !== null
        ? `/oauth/authorize/assignuser?username=${selectedUser}&`
        : '/oauth/authorize?';

    const params = new URLSearchParams({
      response_type: 'token',
      client_id: application.client_id,
      scope: scopesString,
      redirect_uri: getUrl(
        quayConfig.config.LOCAL_OAUTH_HANDLER || '/oauth/localapp',
      ),
    });

    return getUrl(`${base}${params.toString()}`);
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

  const handleAuthModalConfirm = async () => {
    const oauthUrl = generateUrl();
    const jsonUrl =
      oauthUrl + (oauthUrl.includes('?') ? '&' : '?') + 'format=json';

    console.log('🚀 Trying direct API call:', jsonUrl);

    try {
      const response = await fetch(jsonUrl, {
        credentials: 'include',
        headers: {
          Accept: 'application/json',
        },
      });

      console.log('📡 Response status:', response.status);
      console.log('📡 Response headers:', response.headers);

      if (response.ok) {
        const data = await response.json();
        console.log('✅ Response data:', data);
        user;
        // Check if token is directly in the response
        if (data.access_token) {
          console.log('🎉 Token found in response!');
          setGeneratedToken(data.access_token);
          setIsAuthModalOpen(false);
          setIsTokenModalOpen(true);
        } else {
          console.log(
            '🤔 No access_token in response. Available keys:',
            Object.keys(data),
          );
          // Maybe we need to make another call with the CSRF token?
        }
      } else {
        console.error('❌ HTTP Error:', response.status);
      }
    } catch (error) {
      console.error('💥 Fetch failed:', error);
    }
  };

  const handleAuthModalClose = () => {
    setIsAuthModalOpen(false);
  };

  const handleTokenModalClose = () => {
    setIsTokenModalOpen(false);
    setGeneratedToken('');
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
                  {customUser && (
                    <input
                      type="text"
                      placeholder="User"
                      value={selectedUser || ''}
                      onChange={(e) => setSelectedUser(e.target.value)}
                      data-testid="custom-user-input"
                      style={{
                        marginLeft: 'var(--pf-global--spacer--xs)',
                        marginRight: 'var(--pf-global--spacer--xs)',
                      }}
                    />
                  )}
                </Text>
              </FlexItem>
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
        />
      )}

      {props.application && generatedToken && (
        <TokenDisplayModal
          isOpen={isTokenModalOpen}
          onClose={handleTokenModalClose}
          token={generatedToken}
          applicationName={props.application.name}
          scopes={getSelectedScopesList()}
        />
      )}
    </PageSection>
  );
}
