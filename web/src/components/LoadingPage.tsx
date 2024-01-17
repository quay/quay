import React from 'react';
import {
  EmptyState,
  EmptyStateIcon,
  EmptyStateBody,
  Title,
  Spinner,
  Bullseye,
  PageSectionVariants,
  PageSection,
  EmptyStateActions,
  EmptyStateHeader,
  EmptyStateFooter,
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
          <EmptyStateHeader icon={<EmptyStateIcon icon={Spinner} />} />
          <EmptyStateFooter>
            <div tabIndex="1">
              <Title size="lg" headingLevel="h4">
                {props.title ?? 'Loading'}
              </Title>
              <EmptyStateBody>{props.message}</EmptyStateBody>
            </div>
            {props.primaryAction}
            <EmptyStateActions>{props.secondaryActions}</EmptyStateActions>
          </EmptyStateFooter>
        </EmptyState>
      </Bullseye>
    </PageSection>
  );
}
