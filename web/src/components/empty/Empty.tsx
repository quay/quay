import React from 'react';
import {
  EmptyState,
  EmptyStateBody,
  PageSection,
  EmptyStateFooter,
  EmptyStateActions,
} from '@patternfly/react-core';
import {SVGIconProps} from '@patternfly/react-icons/dist/js/createIcon';

export default function Empty(props: EmptyProps) {
  return (
    <PageSection hasBodyWrapper={false}>
      <EmptyState
        headingLevel="h1"
        icon={props.icon}
        titleText={<>{props.title}</>}
        variant="lg"
      >
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
