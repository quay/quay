import {
  Brand,
  Button,
  EmptyState,
  EmptyStateBody,
  EmptyStateIcon,
  PageSection,
  Title,
} from '@patternfly/react-core';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';

// Looks the same as RequestError for now, will update later after
// discussing what this should look like. Keeping as separate component
// for now since it will change in the future.
export default function PageLoadError() {
  return (
    <PageSection>
      <EmptyState variant="full">
        <EmptyStateIcon icon={ExclamationTriangleIcon} />
        <Title headingLevel="h1" size="lg">
          Unable to reach server
        </Title>
        <EmptyStateBody>Page could not be loaded</EmptyStateBody>
        <Button title="Home" onClick={() => window.location.reload()}>
          Retry
        </Button>
      </EmptyState>
    </PageSection>
  );
}
