import React from 'react';
import {
  EmptyState,
  EmptyStateBody,
  Title,
  Spinner,
  Bullseye,
  PageSection,
  EmptyStateActions,
  EmptyStateFooter,
} from '@patternfly/react-core';

export function LoadingPage(props: {
  title?: string | React.ReactNode;
  message?: string | React.ReactNode;
  primaryAction?: React.ReactNode;
  secondaryActions?: React.ReactNode;
}) {
  return (
    <PageSection hasBodyWrapper={false}>
      <Bullseye>
        <EmptyState icon={Spinner}>
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
