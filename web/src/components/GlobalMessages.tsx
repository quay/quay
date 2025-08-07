import React from 'react';
import {
  ExclamationTriangleIcon,
  TimesCircleIcon,
} from '@patternfly/react-icons';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import {useGlobalMessages} from 'src/hooks/UseGlobalMessages';
import {IGlobalMessage} from 'src/resources/GlobalMessagesResource';

// Map severity to subtle background colors (matching Angular)
function severityToStyles(severity: IGlobalMessage['severity']): {
  backgroundColor: string;
  color: string;
} {
  switch (severity) {
    case 'info':
      return {
        backgroundColor: '#F0F8FF', // Very light blue
        color: 'black',
      };
    case 'warning':
      return {
        backgroundColor: '#FFFBF0', // Angular's subtle cream/yellow
        color: 'black',
      };
    case 'error':
      return {
        backgroundColor: '#FFF0F0', // Angular's subtle pink/red
        color: 'black',
      };
    default:
      return {
        backgroundColor: '#F8F9FA', // Light gray
        color: 'black',
      };
  }
}

// Get icon component and color for severity (only warning and error have icons)
function getSeverityIcon(severity: IGlobalMessage['severity']): {
  Icon: React.ComponentType<React.SVGProps<SVGSVGElement>> | null;
  iconColor: string;
} {
  switch (severity) {
    case 'warning':
      return {
        Icon: ExclamationTriangleIcon,
        iconColor: '#E4C212', // Angular's warning yellow
      };
    case 'error':
      return {
        Icon: TimesCircleIcon,
        iconColor: 'red', // Angular's error red
      };
    case 'info':
    default:
      return {
        Icon: null, // No icon for info messages
        iconColor: '',
      };
  }
}

// Component to render a single message
function GlobalMessage({message}: {message: IGlobalMessage}) {
  const styles = severityToStyles(message.severity);
  const {Icon, iconColor} = getSeverityIcon(message.severity);

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
    <div
      style={{
        ...styles,
        padding: '12px 24px',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        fontSize: '14px',
        borderBottom: '1px solid rgba(0,0,0,0.1)',
      }}
    >
      <div style={{display: 'flex', alignItems: 'center'}}>
        {Icon && (
          <Icon
            style={{
              fontSize: '22px',
              color: iconColor,
              marginRight: '10px',
              flexShrink: 0, // Prevent icon from shrinking
            }}
          />
        )}
        <span style={{flex: 1}}>{content}</span>
      </div>
    </div>
  );
}

// Main component that fetches and displays all global messages
export function GlobalMessages() {
  const {data: messages = [], isLoading, error} = useGlobalMessages();

  // Don't render anything while loading or if there's an error
  if (isLoading || error || messages.length === 0) {
    return <></>;
  }

  // Render all messages without Stack component to avoid spacing issues
  return (
    <>
      {messages.map((message) => (
        <GlobalMessage key={message.uuid} message={message} />
      ))}
    </>
  );
}
