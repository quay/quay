import {
  Button,
  EmptyState,
  EmptyStateBody,
  EmptyStateIcon,
  Title,
} from '@patternfly/react-core';
import {
  BanIcon,
  ExclamationCircleIcon,
  PauseCircleIcon,
} from '@patternfly/react-icons';

export function QueuedState() {
  return (
    <EmptyState variant="full">
      <EmptyStateIcon icon={PauseCircleIcon} />
      <Title headingLevel="h1" size="lg">
        Security scan is currently queued.
      </Title>
      <EmptyStateBody>Refresh page for updates in scan status.</EmptyStateBody>
      <Button title="Home" onClick={() => window.location.reload()}>
        Reload
      </Button>
    </EmptyState>
  );
}

export function FailedState() {
  const RedExclamationIcon = () => (
    <ExclamationCircleIcon size="lg" color="red" />
  );
  return (
    <EmptyState variant="full">
      <EmptyStateIcon icon={RedExclamationIcon} />
      <Title headingLevel="h1" size="lg">
        Security scan has failed.
      </Title>
      <EmptyStateBody>
        The scan could not be completed due to error.
      </EmptyStateBody>
    </EmptyState>
  );
}

export function UnsupportedState() {
  return (
    <EmptyState variant="full">
      <EmptyStateIcon icon={BanIcon} />
      <Title headingLevel="h1" size="lg">
        Security scan is not supported.
      </Title>
      <EmptyStateBody>
        Image does not have content the scanner recognizes.
      </EmptyStateBody>
    </EmptyState>
  );
}
