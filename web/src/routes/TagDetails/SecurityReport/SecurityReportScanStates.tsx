import {
  Button,
  EmptyState,
  EmptyStateBody,
  EmptyStateFooter,
  Icon,
} from '@patternfly/react-core';
import {
  BanIcon,
  ExclamationCircleIcon,
  PauseCircleIcon,
} from '@patternfly/react-icons';

export function QueuedState() {
  return (
    <EmptyState
      headingLevel="h1"
      icon={PauseCircleIcon}
      titleText="Security scan is currently queued."
      variant="full"
    >
      <EmptyStateBody>Refresh page for updates in scan status.</EmptyStateBody>
      <EmptyStateFooter>
        <Button title="Home" onClick={() => window.location.reload()}>
          Reload
        </Button>
      </EmptyStateFooter>
    </EmptyState>
  );
}

export function FailedState() {
  const RedExclamationIcon = () => (
    <Icon size="lg">
      <ExclamationCircleIcon color="red" />
    </Icon>
  );
  return (
    <EmptyState
      headingLevel="h1"
      icon={RedExclamationIcon}
      titleText="Security scan has failed."
      variant="full"
    >
      <EmptyStateBody>
        The scan could not be completed due to error.
      </EmptyStateBody>
    </EmptyState>
  );
}

export function UnsupportedState() {
  return (
    <EmptyState
      headingLevel="h1"
      icon={BanIcon}
      titleText="Security scan is not supported."
      variant="full"
    >
      <EmptyStateBody>
        Image does not have content the scanner recognizes.
      </EmptyStateBody>
    </EmptyState>
  );
}
