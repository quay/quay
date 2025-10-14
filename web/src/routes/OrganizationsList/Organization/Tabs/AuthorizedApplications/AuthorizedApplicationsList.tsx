import {
  PageSection,
  PageSectionVariants,
  Text,
  TextContent,
  TextVariants,
  Alert,
  Spinner,
} from '@patternfly/react-core';
import {Table, Thead, Tr, Th, Tbody, Td} from '@patternfly/react-table';
import {ActionsColumn} from '@patternfly/react-table';
import {CubeIcon} from '@patternfly/react-icons';
import {useAuthorizedApplications} from 'src/hooks/UseAuthorizedApplications';

export default function AuthorizedApplicationsList() {
  const {
    authorizedApps,
    assignedApps,
    isLoading,
    error,
    revokeAuthorization,
    deleteAssignedAuthorization,
    getAuthorizationUrl,
    isRevoking,
    isDeletingAssigned,
  } = useAuthorizedApplications();

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
        />
      ) : (
        <Table
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
                  <a
                    href={getAuthorizationUrl(app)}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Authorize Application
                  </a>
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
    </PageSection>
  );
}
