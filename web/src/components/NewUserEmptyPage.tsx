import {
  Button,
  EmptyState,
  EmptyStateBody,
  EmptyStateFooter,
  EmptyStateVariant,
  PageSection,
} from '@patternfly/react-core';
import {UserIcon} from '@patternfly/react-icons';

export default function NewUserEmptyPage(props: NewUserEmptyPageProps) {
  return (
    <PageSection hasBodyWrapper={false}>
      <EmptyState
        headingLevel="h5"
        icon={UserIcon}
        titleText="Welcome to Quay"
        variant={EmptyStateVariant.lg}
      >
        <EmptyStateBody>
          To gain access to organizations and repositories on Quay.io you must{' '}
          <br />
          create a username.
        </EmptyStateBody>
        <EmptyStateFooter>
          <Button
            variant="primary"
            onClick={() => props.setCreateUserModalOpen(true)}
          >
            Create username
          </Button>
        </EmptyStateFooter>
      </EmptyState>
    </PageSection>
  );
}

interface NewUserEmptyPageProps {
  setCreateUserModalOpen: (boolean) => void;
}
