import {PageSection, PageSectionVariants, Title} from '@patternfly/react-core';
import {ChartBarIcon} from '@patternfly/react-icons';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import Empty from 'src/components/empty/Empty';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {Navigate} from 'react-router-dom';

function UsageLogsHeader() {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Usage Logs</Title>
        </div>
      </PageSection>
    </>
  );
}

export default function UsageLogs() {
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
      <UsageLogsHeader />
      <PageSection>
        <Empty
          title="Usage Logs"
          icon={ChartBarIcon}
          body="Usage logs functionality will be implemented here."
        />
      </PageSection>
    </>
  );
}
