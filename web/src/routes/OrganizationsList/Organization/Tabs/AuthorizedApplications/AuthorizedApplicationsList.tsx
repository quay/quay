import {useState, useCallback, useEffect} from 'react';
import {
  PageSection,
  PageSectionVariants,
  Text,
  TextContent,
  TextVariants,
  Alert,
  Spinner,
  Button,
} from '@patternfly/react-core';
import {Table, Thead, Tr, Th, Tbody, Td} from '@patternfly/react-table';
import {ActionsColumn} from '@patternfly/react-table';
import {CubeIcon} from '@patternfly/react-icons';
import {useAuthorizedApplications} from 'src/hooks/UseAuthorizedApplications';
import GenerateTokenAuthorizationModal from 'src/components/modals/GenerateTokenAuthorizationModal';
import TokenDisplayModal from 'src/components/modals/TokenDisplayModal';
import {useAlerts} from 'src/hooks/UseAlerts';
import {AlertVariant} from 'src/atoms/AlertState';
import {GlobalAuthState} from 'src/resources/AuthResource';
import {useQueryClient} from '@tanstack/react-query';

export default function AuthorizedApplicationsList() {
  const {
    authorizedApps,
    assignedApps,
    isLoading,
    error,
    revokeAuthorization,
    deleteAssignedAuthorization,
    getAuthorizationUrl,
    fetchAuthorizationData,
    isRevoking,
    isDeletingAssigned,
  } = useAuthorizedApplications();
  const {addAlert} = useAlerts();
  const queryClient = useQueryClient();

  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authorizationData, setAuthorizationData] = useState<any>(null);
  const [currentApp, setCurrentApp] = useState<any>(null);
  const [oauthPopup, setOauthPopup] = useState<Window | null>(null);
  const [generatedToken, setGeneratedToken] = useState<string | null>(null);
  const [generatedScopes, setGeneratedScopes] = useState<string[]>([]);
  const [isTokenDisplayModalOpen, setIsTokenDisplayModalOpen] = useState(false);

  const handleOAuthMessage = useCallback(
    (event: MessageEvent) => {
      // Verify origin for security
      if (event.origin !== window.location.origin) {
        console.warn('Received message from unexpected origin:', event.origin);
        return;
      }

      if (event.data.type === 'OAUTH_TOKEN_GENERATED') {
        setGeneratedToken(event.data.token);
        setGeneratedScopes(event.data.scope?.split(' ') || []);
        setIsTokenDisplayModalOpen(true);
        setIsAuthModalOpen(false);

        // Invalidate queries to refresh the lists
        queryClient.invalidateQueries(['authorizedApplications']);
        queryClient.invalidateQueries(['assignedAuthorizations']);

        // Clean up popup
        if (oauthPopup && !oauthPopup.closed) {
          oauthPopup.close();
        }
        setOauthPopup(null);
      }
    },
    [oauthPopup, queryClient],
  );

  useEffect(() => {
    window.addEventListener('message', handleOAuthMessage);
    return () => {
      window.removeEventListener('message', handleOAuthMessage);
    };
  }, [handleOAuthMessage]);

  const handleAuthorizeClick = async (app: any) => {
    try {
      const data = await fetchAuthorizationData(app);
      setAuthorizationData(data);
      setCurrentApp(app);
      setIsAuthModalOpen(true);
    } catch (error) {
      console.error('Error fetching authorization data:', error);
      addAlert({
        variant: AlertVariant.Failure,
        title: 'Failed to load authorization data. Please try again.',
      });
    }
  };

  // Convert backend authorization data to modal format
  const getScopesDataFromAuthData = () => {
    if (!authorizationData?.scopes) return {};

    const scopesData: Record<string, any> = {};
    authorizationData.scopes.forEach((scopeInfo: any) => {
      // Backend returns: {title, scope, description, icon, dangerous}
      scopesData[scopeInfo.scope] = {
        title: scopeInfo.title,
        description: scopeInfo.description,
        dangerous: scopeInfo.dangerous,
      };
    });
    return scopesData;
  };

  const getSelectedScopesFromAuthData = () => {
    if (!authorizationData?.scope) return [];
    return authorizationData.scope.split(' ');
  };

  const handleAuthModalConfirm = async () => {
    if (!authorizationData || !currentApp) return;

    setIsAuthModalOpen(false);

    const form = document.createElement('form');
    form.method = 'POST';
    form.target = 'oauth_authorization';
    form.style.display = 'none';
    form.action = '/oauth/authorizeapp';

    const fields = {
      response_type: authorizationData.response_type,
      client_id: authorizationData.client_id,
      redirect_uri: authorizationData.redirect_uri,
      scope: authorizationData.scope,
      state: authorizationData.state || '',
      assignment_uuid: authorizationData.assignment_uuid,
      _csrf_token:
        authorizationData.csrf_token_val || GlobalAuthState.csrfToken,
    };

    Object.entries(fields).forEach(([key, value]) => {
      if (value) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = key;
        input.value = value;
        form.appendChild(input);
      }
    });

    const width = 600;
    const height = 700;
    const left = window.screen.width / 2 - width / 2;
    const top = window.screen.height / 2 - height / 2;

    const popup = window.open(
      '',
      'oauth_authorization',
      `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`,
    );

    if (!popup || popup.closed || typeof popup.closed === 'undefined') {
      addAlert({
        variant: AlertVariant.Warning,
        title:
          'Popup was blocked by your browser. Please allow popups for this site and try again.',
      });
      return;
    }

    setOauthPopup(popup);

    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);

    const checkPopupClosed = setInterval(() => {
      if (popup.closed) {
        clearInterval(checkPopupClosed);
        setOauthPopup(null);
      }
    }, 500);
  };

  const handleAuthModalClose = () => {
    setIsAuthModalOpen(false);
    setAuthorizationData(null);
    setCurrentApp(null);
  };

  if (isLoading) {
    return (
      <PageSection variant={PageSectionVariants.light}>
        <Spinner size="lg" />
      </PageSection>
    );
  }

  if (error) {
    return (
      <PageSection variant={PageSectionVariants.light}>
        <Alert variant="danger" title="Cannot load authorized applications" />
      </PageSection>
    );
  }

  return (
    <PageSection variant={PageSectionVariants.light}>
      <TextContent>
        <Text component={TextVariants.h1}>Authorized Applications</Text>
        <Text component={TextVariants.p}>
          The authorized applications panel lists applications you have
          authorized to view information and perform actions on your behalf. You
          can revoke any of your authorizations by clicking &quot;Revoke
          Authorization&quot; from the kebab menu.
        </Text>
      </TextContent>

      {authorizedApps.length === 0 && assignedApps.length === 0 ? (
        <Alert
          variant="info"
          isInline
          title="You have not authorized any external applications."
          style={{marginTop: '16px'}}
        />
      ) : (
        <Table
          style={{marginTop: '16px'}}
          aria-label="Authorized applications table"
          data-testid="authorized-apps-table"
        >
          <Thead>
            <Tr>
              <Th>Application Name</Th>
              <Th>Authorized Permissions</Th>
              {assignedApps.length > 0 && <Th>Confirm</Th>}
              <Th></Th>
            </Tr>
          </Thead>
          <Tbody>
            {authorizedApps.map((app) => (
              <Tr key={app.uuid}>
                <Td>
                  <div
                    style={{display: 'flex', alignItems: 'center', gap: '8px'}}
                  >
                    <CubeIcon className="app-icon" />
                    {app.application.url ? (
                      <a
                        href={app.application.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={
                          app.application.description || app.application.name
                        }
                      >
                        {app.application.name}
                      </a>
                    ) : (
                      <span
                        title={
                          app.application.description || app.application.name
                        }
                      >
                        {app.application.name}
                      </span>
                    )}
                    <span style={{color: 'var(--pf-v5-global--Color--200)'}}>
                      by {app.application.organization.name}
                    </span>
                  </div>
                </Td>
                <Td>
                  {app.scopes.map((scopeInfo) => (
                    <span
                      key={scopeInfo.scope}
                      className="pf-v5-c-label pf-m-blue"
                      style={{marginRight: '4px'}}
                      title={scopeInfo.description}
                    >
                      {scopeInfo.scope}
                    </span>
                  ))}
                </Td>
                <Td></Td>
                <Td>
                  <ActionsColumn
                    items={[
                      {
                        title: 'Revoke Authorization',
                        onClick: () => revokeAuthorization(app.uuid),
                      },
                    ]}
                  />
                </Td>
              </Tr>
            ))}
            {assignedApps.map((app) => (
              <Tr key={app.uuid}>
                <Td>
                  <div
                    style={{display: 'flex', alignItems: 'center', gap: '8px'}}
                  >
                    <CubeIcon className="app-icon" />
                    {app.application.url ? (
                      <a
                        href={app.application.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={
                          app.application.description || app.application.name
                        }
                      >
                        {app.application.name}
                      </a>
                    ) : (
                      <span
                        title={
                          app.application.description || app.application.name
                        }
                      >
                        {app.application.name}
                      </span>
                    )}
                    <span style={{color: 'var(--pf-v5-global--Color--200)'}}>
                      {app.application.organization.name}
                    </span>
                  </div>
                </Td>
                <Td>
                  {app.scopes.map((scopeInfo) => (
                    <span
                      key={scopeInfo.scope}
                      className="pf-v5-c-label pf-m-blue"
                      style={{marginRight: '4px'}}
                      title={scopeInfo.description}
                    >
                      {scopeInfo.scope}
                    </span>
                  ))}
                </Td>
                <Td>
                  <Button
                    variant="link"
                    isInline
                    onClick={() => handleAuthorizeClick(app)}
                  >
                    Authorize Application
                  </Button>
                </Td>
                <Td>
                  <ActionsColumn
                    items={[
                      {
                        title: 'Delete Authorization',
                        onClick: () => deleteAssignedAuthorization(app.uuid),
                      },
                    ]}
                  />
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      )}

      {authorizationData && currentApp && (
        <GenerateTokenAuthorizationModal
          isOpen={isAuthModalOpen}
          onClose={handleAuthModalClose}
          onConfirm={handleAuthModalConfirm}
          application={{
            name:
              authorizationData.application?.name ||
              currentApp.application.name,
            client_id: authorizationData.client_id,
            description:
              authorizationData.application?.description ||
              currentApp.application.description,
            organization:
              authorizationData.application?.organization ||
              currentApp.application.organization,
          }}
          selectedScopes={getSelectedScopesFromAuthData()}
          scopesData={getScopesDataFromAuthData()}
          hasDangerousScopes={authorizationData.has_dangerous_scopes}
        />
      )}

      {generatedToken && (
        <TokenDisplayModal
          isOpen={isTokenDisplayModalOpen}
          onClose={() => {
            setIsTokenDisplayModalOpen(false);
            setGeneratedToken(null);
            setGeneratedScopes([]);
          }}
          token={generatedToken}
          applicationName={currentApp?.application?.name || 'OAuth Application'}
          scopes={generatedScopes}
        />
      )}
    </PageSection>
  );
}
