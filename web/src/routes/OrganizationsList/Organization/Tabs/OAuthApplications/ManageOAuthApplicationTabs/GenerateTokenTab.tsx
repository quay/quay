import React, {useState} from 'react';
import {
  Alert,
  Button,
  Checkbox,
  Flex,
  FlexItem,
  List,
  ListItem,
  PageSection,
  PageSectionVariants,
  Title,
} from '@patternfly/react-core';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';
import {IOAuthApplication} from 'src/hooks/UseOAuthApplications';
import {OAUTH_SCOPES, OAuthScope} from '../types';

interface GenerateTokenTabProps {
  application: IOAuthApplication | null;
  orgName: string;
}

export default function GenerateTokenTab(props: GenerateTokenTabProps) {
  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);

  if (!props.application) {
    return <div>No application selected</div>;
  }

  // Now we know application is not null, store it in a local variable
  const application = props.application;

  const handleScopeChange = (scope: string, checked: boolean) => {
    if (checked) {
      setSelectedScopes([...selectedScopes, scope]);
    } else {
      setSelectedScopes(selectedScopes.filter((s) => s !== scope));
    }
  };

  const generateTokenUrl = () => {
    const baseUrl = window.location.origin;
    const scopes = selectedScopes.join(' ');
    const params = new URLSearchParams({
      client_id: application.client_id,
      redirect_uri: application.redirect_uri || `${baseUrl}/oauth/callback`,
      response_type: 'code',
      scope: scopes,
    });
    return `${baseUrl}/oauth/authorize?${params.toString()}`;
  };

  const handleGenerateToken = () => {
    if (selectedScopes.length === 0) return;

    const authUrl = generateTokenUrl();
    // Open in new tab
    window.open(authUrl, '_blank');
  };

  const hasDangerousScopes = selectedScopes.some(
    (scope) => OAUTH_SCOPES[scope]?.dangerous,
  );

  return (
    <PageSection variant={PageSectionVariants.light}>
      <Title headingLevel="h3" size="lg">
        Generate Access Token
      </Title>

      <p style={{marginBottom: '1rem'}}>
        Select the permissions (scopes) that this token should have. The
        application will be able to access resources within these scopes on
        behalf of the user.
      </p>

      <Title headingLevel="h4" size="md" style={{marginBottom: '1rem'}}>
        Available Scopes
      </Title>

      <List isPlain>
        {Object.entries(OAUTH_SCOPES).map(
          ([scope, config]: [string, OAuthScope]) => (
            <ListItem key={scope}>
              <Flex
                alignItems={{default: 'alignItemsCenter'}}
                style={{marginBottom: '0.5rem'}}
              >
                <FlexItem>
                  <Checkbox
                    id={`scope-${scope}`}
                    label={
                      <Flex alignItems={{default: 'alignItemsCenter'}}>
                        <FlexItem>
                          <strong>{config.title}</strong>
                        </FlexItem>
                        {config.dangerous && (
                          <FlexItem>
                            <ExclamationTriangleIcon
                              style={{
                                color: 'var(--pf-global--warning-color--100)',
                                marginLeft: '0.5rem',
                              }}
                            />
                          </FlexItem>
                        )}
                      </Flex>
                    }
                    description={config.description}
                    isChecked={selectedScopes.includes(scope)}
                    onChange={(event, checked) =>
                      handleScopeChange(scope, checked)
                    }
                  />
                </FlexItem>
              </Flex>
            </ListItem>
          ),
        )}
      </List>

      {hasDangerousScopes && (
        <Alert
          variant="warning"
          title="Dangerous permissions selected"
          style={{marginTop: '1rem'}}
        >
          Some of the selected permissions can perform destructive actions. Only
          grant these permissions to applications you fully trust.
        </Alert>
      )}

      <Button
        variant="primary"
        onClick={handleGenerateToken}
        isDisabled={selectedScopes.length === 0}
        style={{marginTop: '1rem'}}
      >
        Generate Access Token
      </Button>

      {selectedScopes.length > 0 && (
        <Alert
          variant="info"
          title="Token generation process"
          style={{marginTop: '1rem'}}
        >
          Clicking Generate Access Token will redirect you to the authorization
          page where you can approve access for the selected scopes. After
          approval, you will receive an authorization code that can be exchanged
          for an access token.
        </Alert>
      )}
    </PageSection>
  );
}
