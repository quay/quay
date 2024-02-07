import {
  Button,
  EmptyState,
  EmptyStateBody,
  EmptyStateFooter,
  EmptyStateHeader,
  EmptyStateIcon,
  EmptyStateVariant,
  PageSection,
  PageSectionVariants,
} from '@patternfly/react-core';
import {UserIcon} from '@patternfly/react-icons';

export default function NewUserEmptyPage(props: NewUserEmptyPageProps) {
  return (
    <PageSection variant={PageSectionVariants.light}>
      <EmptyState variant={EmptyStateVariant.lg}>
        <EmptyStateHeader
          titleText="Welcome to Quay"
          icon={<EmptyStateIcon icon={UserIcon} color="black" />}
          headingLevel="h5"
        />
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
