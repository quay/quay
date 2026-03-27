import {
  Button,
  EmptyState,
  EmptyStateBody,
  PageSection,
  EmptyStateFooter,
} from '@patternfly/react-core';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';

// Looks the same as RequestError for now, will update later after
// discussing what this should look like. Keeping as separate component
// for now since it will change in the future.
export default function PageLoadError() {
  return (
    <PageSection hasBodyWrapper={false}>
      <EmptyState
        headingLevel="h1"
        icon={ExclamationTriangleIcon}
        titleText="Unable to reach server"
        variant="full"
      >
        <EmptyStateBody>Page could not be loaded</EmptyStateBody>
        <EmptyStateFooter>
          <Button title="Home" onClick={() => window.location.reload()}>
            Retry
          </Button>
        </EmptyStateFooter>
      </EmptyState>
    </PageSection>
  );
}
