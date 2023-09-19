import {
  EmptyState,
  EmptyStateBody,
  EmptyStateIcon,
  PageSection,
  EmptyStateHeader,
  EmptyStateFooter,
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
        <EmptyStateFooter>{props.button}</EmptyStateFooter>
      </EmptyState>
    </PageSection>
  );
}

interface EmptyProps {
  icon: React.ComponentClass<SVGIconProps, any>;
  title: string;
  body: string;
  button?: JSX.Element;
}
