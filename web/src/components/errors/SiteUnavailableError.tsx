import {
  Button,
  EmptyState,
  EmptyStateBody,
  EmptyStateIcon,
  Page,
  PageSection,
  Title,
} from '@patternfly/react-core';
import {ExclamationCircleIcon} from '@patternfly/react-icons';

export default function SiteUnavailableError() {
  return (
    <Page>
      <PageSection>
        <EmptyState variant="full">
          <EmptyStateIcon icon={ExclamationCircleIcon} />
          <Title headingLevel="h1" size="lg">
            This site is temporarily unavailable
          </Title>
          <EmptyStateBody>
            Try refreshing the page. If the problem persists, contact your
            organization administrator or visit our{' '}
            <a href="https://status.quay.io/">status page</a> for known outages.
          </EmptyStateBody>
          <Button title="Home" onClick={() => window.location.reload()}>
            Reload
          </Button>
        </EmptyState>
      </PageSection>
    </Page>
  );
}
