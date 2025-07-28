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
  TextVariants,
} from '@patternfly/react-core';
import {InfoCircleIcon} from '@patternfly/react-icons';
import {useForm} from 'react-hook-form';
import {IOAuthApplication} from 'src/hooks/UseOAuthApplications';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {FormCheckbox} from 'src/components/forms/FormCheckbox';
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
    const url = generateUrl();
    window.open(url, '_blank');
  };

  const assignUser = () => {
    setCustomUser(true);
  };

  const cancelAssignUser = () => {
    setSelectedUser(null);
    setCustomUser(false);
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
            <Text component={TextVariants.p}>
              <Flex
                spaceItems={{default: 'spaceItemsSm'}}
                alignItems={{default: 'alignItemsCenter'}}
              >
                <FlexItem>
                  The generated token will act on behalf of user{' '}
                  {!customUser && <strong>{user?.username || 'user'}</strong>}
                  {customUser && (
                    <input
                      type="text"
                      placeholder="User"
                      value={selectedUser || ''}
                      onChange={(e) => setSelectedUser(e.target.value)}
                      style={{
                        marginLeft: 'var(--pf-global--spacer--xs)',
                        marginRight: 'var(--pf-global--spacer--xs)',
                      }}
                    />
                  )}
                </FlexItem>
                <FlexItem>
                  {!customUser ? (
                    <Button variant="primary" size="sm" onClick={assignUser}>
                      Assign another user
                    </Button>
                  ) : (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={cancelAssignUser}
                    >
                      Cancel
                    </Button>
                  )}
                </FlexItem>
              </Flex>
            </Text>
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
            >
              Generate Access Token
            </Button>
          ) : (
            <Button
              variant="primary"
              onClick={handleGenerateToken}
              isDisabled={!selectedUser || getSelectedScopesList().length === 0}
            >
              Assign token
            </Button>
          )}
        </StackItem>
      </Stack>
    </PageSection>
  );
}
