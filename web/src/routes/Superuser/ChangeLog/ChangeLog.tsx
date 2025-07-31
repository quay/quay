import {PageSection, PageSectionVariants, Title} from '@patternfly/react-core';
import {ListIcon} from '@patternfly/react-icons';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import Empty from 'src/components/empty/Empty';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {Navigate} from 'react-router-dom';

function ChangeLogHeader() {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Change Log</Title>
        </div>
      </PageSection>
    </>
  );
}

export default function ChangeLog() {
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
      <ChangeLogHeader />
      <PageSection>
        <Empty
          title="Change Log"
          icon={ListIcon}
          body="Change log functionality will be implemented here."
        />
      </PageSection>
    </>
  );
}
