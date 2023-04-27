import {
  Page,
  PageSection,
  PageSectionVariants,
  EmptyState,
  EmptyStateVariant,
  EmptyStateIcon,
  Title,
  EmptyStateBody,
  Button,
} from '@patternfly/react-core';
import {UserIcon} from "@patternfly/react-icons";

export default function NewUserEmptyPage(props: NewUserEmptyPageProps) {
  return (
    <Page>
      <PageSection variant={PageSectionVariants.light}>
        <EmptyState variant={EmptyStateVariant.large}>
          <EmptyStateIcon icon={UserIcon} color='black'/>
          <Title headingLevel="h5" size="4xl">
            Welcome to Quay
          </Title>
          <EmptyStateBody>
            To gain access to organizations and repositories on Quay.io you must <br />
            create a username.
          </EmptyStateBody>
          <Button variant="primary" onClick={() => props.setCreateUserModalOpen(true)}>Create username</Button>
        </EmptyState>
      </PageSection>
    </Page>
  );
}

interface NewUserEmptyPageProps {
  setCreateUserModalOpen: (boolean) => void;
}
