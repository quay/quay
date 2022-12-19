import React from 'react';
import {
  EmptyState,
  EmptyStateIcon,
  EmptyStateBody,
  EmptyStateSecondaryActions,
  Title,
  Spinner,
  Bullseye,
  PageSectionVariants,
  PageSection,
} from '@patternfly/react-core';

export function LoadingPage(props: {
  title?: string | React.ReactNode;
  message?: string | React.ReactNode;
  primaryAction?: React.ReactNode;
  secondaryActions?: React.ReactNode;
}) {
  return (
    <PageSection variant={PageSectionVariants.light}>
      <Bullseye>
        <EmptyState>
          <EmptyStateIcon variant="container" component={Spinner} />
          <div>
            <Title size="lg" headingLevel="h4">
              {props.title ?? 'Loading'}
            </Title>
            <EmptyStateBody>{props.message}</EmptyStateBody>
          </div>
          {props.primaryAction}
          <EmptyStateSecondaryActions>
            {props.secondaryActions}
          </EmptyStateSecondaryActions>
        </EmptyState>
      </Bullseye>
    </PageSection>
  );
}
