import {
  PageSection,
  PageSectionVariants,
  Title,
  Button,
  Spinner,
  Alert,
  Modal,
  ModalVariant,
  Dropdown,
  DropdownList,
  DropdownItem,
  MenuToggle,
} from '@patternfly/react-core';
import {
  EnvelopeIcon,
  PlusIcon,
  ExclamationTriangleIcon,
  InfoCircleIcon,
  TimesCircleIcon,
  TrashIcon,
  CogIcon,
} from '@patternfly/react-icons';
import {Table, Thead, Tr, Th, Tbody, Td} from '@patternfly/react-table';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import {useState} from 'react';
import {QuayBreadcrumb} from 'src/components/breadcrumb/Breadcrumb';
import Empty from 'src/components/empty/Empty';
import {useCurrentUser} from 'src/hooks/UseCurrentUser';
import {
  useGlobalMessages,
  useDeleteGlobalMessage,
} from 'src/hooks/UseGlobalMessages';
import {Navigate} from 'react-router-dom';
import {IGlobalMessage} from 'src/resources/GlobalMessagesResource';
import {CreateMessageForm} from './CreateMessageForm';

function MessagesHeader({onCreateMessage}: {onCreateMessage: () => void}) {
  return (
    <>
      <QuayBreadcrumb />
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <div
          className="co-m-nav-title--row"
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Title headingLevel="h1">Messages</Title>
          <Button
            variant="primary"
            icon={<PlusIcon />}
            onClick={onCreateMessage}
          >
            Create Message
          </Button>
        </div>
      </PageSection>
    </>
  );
}

// Component to render message content (markdown or plain text)
function MessageContent({message}: {message: IGlobalMessage}) {
  if (message.media_type === 'text/markdown') {
    return (
      <Markdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          a: ({href, children, ...props}) => {
            const isExternal = href?.startsWith('http');
            return (
              <a
                {...props}
                href={href}
                target={isExternal ? '_blank' : undefined}
                rel={isExternal ? 'noopener noreferrer' : undefined}
              >
                {children}
              </a>
            );
          },
          p: ({children}) => <div>{children}</div>,
        }}
      >
        {message.content}
      </Markdown>
    );
  }
  return <span>{message.content}</span>;
}

// Component to render severity with icon and badge (matching other table patterns)
function SeverityDisplay({severity}: {severity: IGlobalMessage['severity']}) {
  const severityConfig = {
    info: {
      icon: InfoCircleIcon,
      color: '#428BCA', // Blue like other tables
      label: 'info',
    },
    warning: {
      icon: ExclamationTriangleIcon,
      color: '#FCA657', // Orange like ServiceKeys
      label: 'warning',
    },
    error: {
      icon: TimesCircleIcon,
      color: '#D64456', // Red like ServiceKeys
      label: 'error',
    },
  };

  const config = severityConfig[severity];
  const Icon = config.icon;

  return (
    <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
      <Icon style={{color: config.color}} />
      <span style={{fontWeight: 500}}>{config.label}</span>
    </div>
  );
}

export default function Messages() {
  const {isSuperUser, loading: userLoading} = useCurrentUser();
  const {
    data: messages = [],
    isLoading: messagesLoading,
    error: messagesError,
  } = useGlobalMessages();
  const deleteMessage = useDeleteGlobalMessage();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [messageToDelete, setMessageToDelete] = useState<IGlobalMessage | null>(
    null,
  );
  const [openActionMenus, setOpenActionMenus] = useState<
    Record<string, boolean>
  >({});

  if (userLoading) {
    return null;
  }

  // Redirect non-superusers
  if (!isSuperUser) {
    return <Navigate to="/organization" replace />;
  }

  const handleDeleteMessage = (message: IGlobalMessage) => {
    setMessageToDelete(message);
    setIsDeleteModalOpen(true);
  };

  const confirmDeleteMessage = async () => {
    if (!messageToDelete) return;

    try {
      await deleteMessage.mutateAsync(messageToDelete.uuid);
      setIsDeleteModalOpen(false);
      setMessageToDelete(null);
    } catch (error) {
      console.error('Failed to delete message:', error);
      setIsDeleteModalOpen(false);
      setMessageToDelete(null);
    }
  };

  const cancelDeleteMessage = () => {
    setIsDeleteModalOpen(false);
    setMessageToDelete(null);
  };

  const handleCreateMessage = () => {
    setIsCreateModalOpen(true);
  };

  // Action menu helpers (matching ServiceKeys pattern)
  const isActionMenuOpen = (messageId: string) => {
    return openActionMenus[messageId] || false;
  };

  const setActionMenuOpen = (messageId: string, isOpen: boolean) => {
    setOpenActionMenus((prev) => ({
      ...prev,
      [messageId]: isOpen,
    }));
  };

  const renderContent = () => {
    if (messagesLoading) {
      return (
        <div style={{textAlign: 'center', padding: '2rem'}}>
          <Spinner size="lg" />
        </div>
      );
    }

    if (messagesError) {
      return (
        <Alert variant="danger" title="Error Loading Messages">
          Failed to load global messages. Please try again.
        </Alert>
      );
    }

    if (messages.length === 0) {
      return (
        <Empty
          title="No Messages"
          icon={EnvelopeIcon}
          body="No global messages have been created yet. Click 'Create Message' to add one."
        />
      );
    }

    return (
      <Table aria-label="Global Messages" variant="compact">
        <Thead>
          <Tr>
            <Th>Message</Th>
            <Th>Severity</Th>
            <Th></Th>
          </Tr>
        </Thead>
        <Tbody>
          {messages.map((message) => (
            <Tr key={message.uuid}>
              <Td>
                <MessageContent message={message} />
              </Td>
              <Td>
                <SeverityDisplay severity={message.severity} />
              </Td>
              <Td>
                <Dropdown
                  toggle={(toggleRef) => (
                    <MenuToggle
                      ref={toggleRef}
                      id={`${message.uuid}-actions-toggle`}
                      data-testid={`${message.uuid}-actions-toggle`}
                      variant="plain"
                      onClick={() =>
                        setActionMenuOpen(
                          message.uuid,
                          !isActionMenuOpen(message.uuid),
                        )
                      }
                      isExpanded={isActionMenuOpen(message.uuid)}
                    >
                      <CogIcon />
                    </MenuToggle>
                  )}
                  isOpen={isActionMenuOpen(message.uuid)}
                  onOpenChange={(isOpen) =>
                    setActionMenuOpen(message.uuid, isOpen)
                  }
                  popperProps={{
                    enableFlip: true,
                    position: 'right',
                  }}
                >
                  <DropdownList>
                    <DropdownItem
                      key="delete"
                      onClick={() => {
                        handleDeleteMessage(message);
                        setActionMenuOpen(message.uuid, false);
                      }}
                      isDisabled={deleteMessage.isLoading}
                      icon={<TrashIcon />}
                    >
                      Delete Message
                    </DropdownItem>
                  </DropdownList>
                </Dropdown>
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    );
  };

  return (
    <>
      <MessagesHeader onCreateMessage={handleCreateMessage} />
      <PageSection>{renderContent()}</PageSection>

      {/* Create Message Modal */}
      <CreateMessageForm
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
      />

      {/* Delete Confirmation Modal */}
      <Modal
        variant={ModalVariant.small}
        title="Delete Message?"
        isOpen={isDeleteModalOpen}
        onClose={cancelDeleteMessage}
        actions={[
          <Button
            key="delete"
            variant="danger"
            onClick={confirmDeleteMessage}
            isLoading={deleteMessage.isLoading}
            isDisabled={deleteMessage.isLoading}
          >
            Delete Message
          </Button>,
          <Button key="cancel" variant="link" onClick={cancelDeleteMessage}>
            Cancel
          </Button>,
        ]}
      >
        Are you sure you want to delete this message? This action cannot be
        undone.
      </Modal>
    </>
  );
}
