import {
  Button,
  EmptyState,
  EmptyStateBody,
  PageSection,
  EmptyStateFooter,
} from '@patternfly/react-core';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';

export default function RequestError(props: RequestErrorProps) {
  return (
    <PageSection hasBodyWrapper={false}>
      <EmptyState
        headingLevel="h1"
        icon={ExclamationTriangleIcon}
        titleText="Unable to complete request"
        variant="full"
      >
        <EmptyStateBody>{props.message}</EmptyStateBody>
        <EmptyStateFooter>
          <Button title="Home" onClick={() => window.location.reload()}>
            Retry
          </Button>
        </EmptyStateFooter>
      </EmptyState>
    </PageSection>
  );
}

interface RequestErrorProps {
  message: string;
}
