import React from 'react';
import {Banner, Stack} from '@patternfly/react-core';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import {useGlobalMessages} from 'src/hooks/UseGlobalMessages';
import {IGlobalMessage} from 'src/resources/GlobalMessagesResource';

// Map severity to PatternFly Banner variant
function severityToBannerVariant(
  severity: IGlobalMessage['severity'],
): 'default' | 'blue' | 'red' | 'gold' | 'green' {
  switch (severity) {
    case 'info':
      return 'blue';
    case 'warning':
      return 'gold';
    case 'error':
      return 'red';
    default:
      return 'default';
  }
}

// Component to render a single message
function GlobalMessage({message}: {message: IGlobalMessage}) {
  const variant = severityToBannerVariant(message.severity);

  const content =
    message.media_type === 'text/markdown' ? (
      <Markdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          // Ensure links open in new tab for external URLs
          a: ({href, children, ...props}) => {
            const isExternal = href?.startsWith('http');
            return (
              <a
                {...props}
                href={href}
                target={isExternal ? '_blank' : undefined}
                rel={isExternal ? 'noopener noreferrer' : undefined}
                style={{color: 'inherit', textDecoration: 'underline'}}
              >
                {children}
              </a>
            );
          },
          // Keep paragraphs inline for banner content
          p: ({children}) => <span>{children}</span>,
        }}
      >
        {message.content}
      </Markdown>
    ) : (
      message.content
    );

  return (
    <Banner variant={variant} isSticky>
      {content}
    </Banner>
  );
}

// Main component that fetches and displays all global messages
export function GlobalMessages() {
  const {data: messages = [], isLoading, error} = useGlobalMessages();

  // Don't render anything while loading or if there's an error
  if (isLoading || error || messages.length === 0) {
    return null;
  }

  // If there's only one message, render it directly
  if (messages.length === 1) {
    return <GlobalMessage message={messages[0]} />;
  }

  // If there are multiple messages, stack them
  return (
    <Stack hasGutter={false}>
      {messages.map((message) => (
        <GlobalMessage key={message.uuid} message={message} />
      ))}
    </Stack>
  );
}
