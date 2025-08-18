import {
  Button,
  EmptyState,
  EmptyStateBody,
  EmptyStateIcon,
  Page,
  PageSection,
  EmptyStateHeader,
  EmptyStateFooter,
} from '@patternfly/react-core';
import {ExclamationCircleIcon} from '@patternfly/react-icons';

export default function SiteUnavailableError() {
  return (
    <Page>
      <PageSection>
        <EmptyState variant="full">
          <EmptyStateHeader
            titleText="This site is temporarily unavailable"
            icon={<EmptyStateIcon icon={ExclamationCircleIcon} />}
            headingLevel="h1"
          />
          <EmptyStateBody>
            {window?.location?.hostname === 'quay.io' ||
            window?.location?.hostname === 'stage.quay.io' ? (
              <>
                Try refreshing the page. If the problem persists, contact your
                organization administrator or visit our{' '}
                <a href="https://status.redhat.com">status page</a> for known
                outages.
              </>
            ) : (
              'Try refreshing the page. If the problem persists, contact your organization administrator.'
            )}
          </EmptyStateBody>
          <EmptyStateFooter>
            <Button title="Home" onClick={() => window.location.reload()}>
              Reload
            </Button>
          </EmptyStateFooter>
        </EmptyState>
      </PageSection>
    </Page>
  );
}
