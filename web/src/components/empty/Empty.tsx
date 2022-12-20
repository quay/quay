import {
  EmptyState,
  EmptyStateBody,
  EmptyStateIcon,
  PageSection,
  Title,
} from '@patternfly/react-core';
import {SVGIconProps} from '@patternfly/react-icons/dist/js/createIcon';

export default function Empty(props: EmptyProps) {
  return (
    <PageSection>
      <EmptyState variant="large">
        <EmptyStateIcon icon={props.icon} />
        <Title headingLevel="h1" size="lg">
          {props.title}
        </Title>
        <EmptyStateBody style={{paddingBottom: 20}}>
          {props.body}
        </EmptyStateBody>
        {props.button}
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
