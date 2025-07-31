import {PageSection, PageSectionVariants, Title} from '@patternfly/react-core';
import {KeyIcon} from '@patternfly/react-icons';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import Empty from 'src/components/empty/Empty';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {Navigate} from 'react-router-dom';

function ServiceKeysHeader() {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Service Keys</Title>
        </div>
      </PageSection>
    </>
  );
}

export default function ServiceKeys() {
  const {isSuperUser, loading} = useCurrentUser();

  if (loading) {
    return null;
  }

  // Redirect non-superusers
  if (!isSuperUser) {
    return <Navigate to="/organization" replace />;
  }
  return (
    <>
      <ServiceKeysHeader />
      <PageSection>
        <Empty
          title="Service Keys"
          icon={KeyIcon}
          body="Service keys management functionality will be implemented here."
        />
      </PageSection>
    </>
  );
}
