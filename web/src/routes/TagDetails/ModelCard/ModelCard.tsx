import {PageSection, Divider, TextContent} from '@patternfly/react-core';

import {Remark} from 'react-remark';

export function ModelCard(props: ModelCardProps) {
  return (
    <>
      <Divider />
      <PageSection>
        <TextContent>
          <Remark>{props.modelCard}</Remark>
        </TextContent>
      </PageSection>
    </>
  );
}

interface ModelCardProps {
  modelCard: string;
}
