import {PageSection, PageSectionVariants, Title} from '@patternfly/react-core';
import {EnvelopeIcon} from '@patternfly/react-icons';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import Empty from 'src/components/empty/Empty';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {Navigate} from 'react-router-dom';

function MessagesHeader() {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div className="co-m-nav-title--row">
          <Title headingLevel="h1">Messages</Title>
        </div>
      </PageSection>
    </>
  );
}

export default function Messages() {
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
      <MessagesHeader />
      <PageSection>
        <Empty
          title="Messages"
          icon={EnvelopeIcon}
          body="Global messages functionality will be implemented here."
        />
      </PageSection>
    </>
  );
}
