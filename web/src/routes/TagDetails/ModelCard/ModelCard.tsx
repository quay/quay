import {PageSection, Divider, TextContent} from '@patternfly/react-core';

import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

export function ModelCard(props: ModelCardProps) {
  const modelcard = props.modelCard;

  return (
    <>
      <Divider />
      <PageSection>
        <TextContent>
          <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
            {modelcard}
          </Markdown>
        </TextContent>
      </PageSection>
    </>
  );
}

interface ModelCardProps {
  modelCard: string;
}
