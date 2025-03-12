import {PageSection, Divider, TextContent} from '@patternfly/react-core';

import {Remark} from 'react-remark';
import remarkGfm from 'remark-gfm';
import oembed from '@agentofuser/remark-oembed';

export function ModelCard(props: ModelCardProps) {
  return (
    <>
      <Divider />
      <PageSection>
        <TextContent>
          <Remark remarkPlugins={[remarkGfm, oembed]}>{props.modelCard}</Remark>
        </TextContent>
      </PageSection>
    </>
  );
}

interface ModelCardProps {
  modelCard: string;
}
