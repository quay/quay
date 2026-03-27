import {
  Button,
  EmptyState,
  EmptyStateBody,
  Page,
  PageSection,
  EmptyStateFooter,
} from '@patternfly/react-core';
import {ExclamationCircleIcon} from '@patternfly/react-icons';

export default function SiteUnavailableError() {
  return (
    <Page>
      <PageSection hasBodyWrapper={false}>
        <EmptyState
          headingLevel="h1"
          icon={ExclamationCircleIcon}
          titleText="This site is temporarily unavailable"
          variant="full"
        >
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
