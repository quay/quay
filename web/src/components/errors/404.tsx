import {EmptyState, EmptyStateBody, PageSection} from '@patternfly/react-core';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';

export default function NotFound() {
  return (
    <PageSection hasBodyWrapper={false}>
      <EmptyState
        headingLevel="h1"
        icon={ExclamationTriangleIcon}
        titleText="404 Page not found"
        variant="full"
      >
        <EmptyStateBody>
          We didn&apos;t find a page that matches the address you navigated to.
        </EmptyStateBody>
      </EmptyState>
    </PageSection>
  );
}
