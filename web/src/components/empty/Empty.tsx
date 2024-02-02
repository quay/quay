import React from 'react';
import {
  EmptyState,
  EmptyStateBody,
  EmptyStateIcon,
  PageSection,
  EmptyStateHeader,
  EmptyStateFooter,
  EmptyStateActions,
} from '@patternfly/react-core';
import {SVGIconProps} from '@patternfly/react-icons/dist/js/createIcon';

export default function Empty(props: EmptyProps) {
  return (
    <PageSection>
      <EmptyState variant="lg">
        <EmptyStateHeader
          titleText={<>{props.title}</>}
          icon={<EmptyStateIcon icon={props.icon} />}
          headingLevel="h1"
        />
        <EmptyStateBody style={{paddingBottom: 20}}>
          {props.body}
        </EmptyStateBody>
        <EmptyStateFooter>
          <EmptyStateActions variant="primary">
            {props.button}
          </EmptyStateActions>
          {props.secondaryActions?.map((ele) => ele)}
        </EmptyStateFooter>
      </EmptyState>
    </PageSection>
  );
}

interface EmptyProps {
  icon: React.ComponentClass<SVGIconProps, unknown>;
  title: string;
  body: string;
  button?: JSX.Element;
  secondaryActions?: JSX.Element[];
}
