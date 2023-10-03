import {
  Button,
  EmptyState,
  EmptyStateBody,
  EmptyStateIcon,
  PageSection,
  PageSectionVariants,
  EmptyStateHeader,
  EmptyStateFooter,
} from '@patternfly/react-core';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';

export default function RequestError(props: RequestErrorProps) {
  return (
    <PageSection variant={PageSectionVariants.light}>
      <EmptyState variant="full">
        <EmptyStateHeader
          titleText="Unable to complete request"
          icon={<EmptyStateIcon icon={ExclamationTriangleIcon} />}
          headingLevel="h1"
        />
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
