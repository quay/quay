import {
  PageSection,
  PageSectionVariants,
  Text,
  TextContent,
  TextVariants,
  Alert,
} from '@patternfly/react-core';
import {Table, Thead, Tr, Th, Tbody, Td} from '@patternfly/react-table';
import {useExternalLoginManagement} from 'src/hooks/UseExternalLoginManagement';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {ExternalLoginButton} from 'src/components/ExternalLoginButton';
import {IconImageView} from 'src/components/IconImageView';
import AuthorizedApplicationsList from '../AuthorizedApplications/AuthorizedApplicationsList';
import './ExternalLoginsList.css';

export default function ExternalLoginsList() {
  const quayConfig = useQuayConfig();
  const {
    externalLogins,
    externalLoginInfo,
    isProviderAttached,
    detachExternalLogin,
  } = useExternalLoginManagement();

  const handleDetach = async (providerId: string) => {
    try {
      await detachExternalLogin(providerId);
      // Refresh will happen via query invalidation
    } catch (error) {
      console.error('Failed to detach external login:', error);
    }
  };

  if (!externalLogins || externalLogins.length === 0) {
    return (
      <PageSection variant={PageSectionVariants.light}>
        <Alert
          variant="info"
          isInline
          title="No external login providers configured"
          data-testid="no-external-providers-alert"
        >
          External login providers have not been configured for this Quay
          instance.
        </Alert>
      </PageSection>
    );
  }

  return (
    <>
      <PageSection
        variant={PageSectionVariants.light}
        data-testid="external-logins-tab"
      >
        <TextContent>
          <Text component={TextVariants.h1}>External Logins</Text>
          <Text component={TextVariants.p}>
            The external logins panel lists all supported external login
            providers, which can be used for one-click OAuth-based login to
            Quay. Accounts can be attached or detached by clicking the
            associated button below.
          </Text>
        </TextContent>

        <Table
          aria-label="External login providers table"
          className="external-logins-table"
          data-testid="external-logins-table"
        >
          <Thead>
            <Tr>
              <Th>Provider</Th>
              <Th>Account Status</Th>
              {quayConfig?.features?.DIRECT_LOGIN && <Th>Attach/Detach</Th>}
            </Tr>
          </Thead>
          <Tbody>
            {externalLogins.map((provider) => {
              const isAttached = isProviderAttached(provider.id);
              const loginInfo = externalLoginInfo[provider.id];

              return (
                <Tr key={provider.id}>
                  <Td>
                    <div className="provider-info">
                      <IconImageView
                        value={provider.icon}
                        className="provider-icon"
                      />
                      {provider.title}
                    </div>
                  </Td>
                  <Td data-testid={`provider-status-${provider.id}`}>
                    {isAttached ? (
                      <span className="account-status-attached">
                        Attached to {provider.title} account
                        {loginInfo?.metadata?.service_username && (
                          <strong style={{marginLeft: '4px'}}>
                            {loginInfo.metadata.service_username}
                          </strong>
                        )}
                      </span>
                    ) : (
                      <span className="account-status-unattached">
                        Not attached to {provider.title}
                      </span>
                    )}
                  </Td>
                  {quayConfig?.features?.DIRECT_LOGIN && (
                    <Td>
                      {!isAttached ? (
                        <ExternalLoginButton
                          provider={provider}
                          action="attach"
                          isLink={true}
                        />
                      ) : (
                        <button
                          type="button"
                          className="signin-link-button"
                          onClick={() => handleDetach(provider.id)}
                          data-testid={`detach-${provider.id}`}
                        >
                          Detach Account
                        </button>
                      )}
                    </Td>
                  )}
                </Tr>
              );
            })}
          </Tbody>
        </Table>
      </PageSection>

      <div style={{margin: '25px 0'}} />

      {/* Add Authorized Applications section */}
      <AuthorizedApplicationsList />
    </>
  );
}
