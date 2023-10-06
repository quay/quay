import React from 'react';
import {
  EmptyState,
  EmptyStateBody,
  EmptyStateIcon,
  Page,
  PageSection,
  EmptyStateHeader,
} from '@patternfly/react-core';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';

export default function NotFound() {
  return (
    <Page>
      <PageSection>
        <EmptyState variant="full">
          <EmptyStateHeader
            titleText="404 Page not found"
            icon={<EmptyStateIcon icon={ExclamationTriangleIcon} />}
            headingLevel="h1"
          />
          <EmptyStateBody>
            We didn&apos;t find a page that matches the address you navigated
            to.
          </EmptyStateBody>
        </EmptyState>
      </PageSection>
    </Page>
  );
}
