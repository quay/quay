import React from 'react';
import {
  CodeBlock,
  CodeBlockAction,
  CodeBlockCode,
  ClipboardCopyButton,
} from '@patternfly/react-core';
import {PageSection, Divider, Content} from '@patternfly/react-core';
import {Table, Th, Td} from '@patternfly/react-table';

import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeVideo from 'rehype-video';

export const MarkdownCodeBlock: React.FunctionComponent = (props) => {
  const [copied, setCopied] = React.useState(false);

  const clipboardCopyFunc = (event, text) => {
    navigator.clipboard.writeText(text.toString());
  };

  const onClick = (event, text) => {
    clipboardCopyFunc(event, text);
    setCopied(true);
  };

  const actions = (
    <React.Fragment>
      <CodeBlockAction>
        <ClipboardCopyButton
          id="basic-copy-button"
          textId="code-content"
          aria-label="Copy to clipboard"
          onClick={(e) => onClick(e, props.code)}
          exitDelay={copied ? 1500 : 600}
          maxWidth="110px"
          variant="plain"
          onTooltipHidden={() => setCopied(false)}
        >
          {copied ? 'Successfully copied to clipboard!' : 'Copy to clipboard'}
        </ClipboardCopyButton>
      </CodeBlockAction>
    </React.Fragment>
  );

  return (
    <CodeBlock actions={actions}>
      <CodeBlockCode id="code-content">{props.code}</CodeBlockCode>
    </CodeBlock>
  );
};

export function ModelCard(props: ModelCardProps) {
  const modelcard = props.modelCard;
  const isValidImgSrc = (src) =>
    src &&
    (src.startsWith('https://github.com/') ||
      src.startsWith('https://huggingface.co/'));

  return (
    <>
      <Divider />
      <PageSection hasBodyWrapper={false}>
        <Content>
          <Markdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[
              [rehypeRaw],
              [
                rehypeVideo,
                {
                  test: new RegExp(
                    '(.*)(githubusercontent.com|github.com|huggingface.co)(.*)(.mp4|.mov)$',
                  ),
                },
              ],
            ]}
            components={{
              code({node, inline, className, children, ...props}) {
                return <MarkdownCodeBlock code={children} />;
              },
              table: ({children}) => (
                <Table borders={true} variant={'compact'}>
                  {children}
                </Table>
              ),
              caption: 'Caption',
              th: ({children}) => (
                <Th style={{border: '1px solid black', padding: '8px'}}>
                  {children}
                </Th>
              ),
              td: ({children}) => (
                <Td style={{border: '1px solid black', padding: '8px'}}>
                  {children}
                </Td>
              ),
              img: ({src, alt}) =>
                isValidImgSrc(src) ? (
                  <img src={src} alt={alt} style={{maxWidth: '100%'}} />
                ) : null,
              iframe: () => null,
            }}
          >
            {modelcard}
          </Markdown>
        </Content>
      </PageSection>
    </>
  );
}

interface ModelCardProps {
  modelCard: string;
}
