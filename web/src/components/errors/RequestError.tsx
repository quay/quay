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
import {getErrorMessageFromUnknown} from 'src/resources/ErrorHandling';

export default function RequestError(props: RequestErrorProps) {
  const capitalizeFirstLetter = (str: string) => {
    return str.charAt(0).toUpperCase() + str.slice(1);
  };

  const errorMessage = props.message || getErrorMessageFromUnknown(props.err);
  const message = capitalizeFirstLetter(errorMessage);
  const title =
    props.title !== undefined ? props.title : 'Unable to complete request';

  return (
    <PageSection variant={PageSectionVariants.light}>
      <EmptyState variant="full">
        {title && (
          <EmptyStateHeader
            titleText={title}
            icon={<EmptyStateIcon icon={ExclamationTriangleIcon} />}
            headingLevel="h1"
          />
        )}
        <EmptyStateBody>{message}</EmptyStateBody>
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
  err?: unknown;
  message?: string;
  title?: string;
}
