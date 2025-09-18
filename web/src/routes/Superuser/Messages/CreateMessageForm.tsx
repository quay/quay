import {
  Modal,
  ModalVariant,
  Button,
  Form,
  FormGroup,
  FormSelect,
  FormSelectOption,
  Tab,
  TabTitleText,
  Tabs,
  TextArea,
  Toolbar,
  ToolbarContent,
  ToolbarGroup,
  ToolbarItem,
  Card,
  CardBody,
} from '@patternfly/react-core';
import {
  BoldIcon,
  ItalicIcon,
  ListIcon,
  LinkIcon,
  CodeIcon,
  QuoteLeftIcon,
} from '@patternfly/react-icons';
import {useState} from 'react';
import {useForm, Controller} from 'react-hook-form';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import {useCreateGlobalMessage} from 'src/hooks/UseGlobalMessages';

interface CreateMessageFormData {
  severity: 'info' | 'warning' | 'error';
  content: string;
}

interface CreateMessageFormProps {
  isOpen: boolean;
  onClose: () => void;
  freshLogin?: {
    showFreshLoginModal: (retryOperation: () => Promise<void>) => void;
    isFreshLoginRequired: (error: unknown) => boolean;
  };
}

export function CreateMessageForm({
  isOpen,
  onClose,
  freshLogin,
}: CreateMessageFormProps) {
  const [activeTabKey, setActiveTabKey] = useState<string | number>('write');
  const createMessage = useCreateGlobalMessage();

  const formHook = useForm<CreateMessageFormData>({
    defaultValues: {
      severity: 'info',
      content: '',
    },
  });

  const {handleSubmit, control, formState, watch, setValue} = formHook;

  const currentContent = watch('content');

  // Markdown toolbar functions
  const insertMarkdown = (before: string, after = '') => {
    const textarea = document.getElementById(
      'message-content',
    ) as HTMLTextAreaElement;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const selectedText = text.substring(start, end);

    const newText =
      text.substring(0, start) +
      before +
      selectedText +
      after +
      text.substring(end);

    setValue('content', newText);

    // Focus and set cursor position
    setTimeout(() => {
      textarea.focus();
      const newCursorPos = start + before.length + selectedText.length;
      textarea.setSelectionRange(newCursorPos, newCursorPos);
    }, 0);
  };

  const onSubmit = async (data: CreateMessageFormData) => {
    try {
      await createMessage.mutateAsync({
        message: {
          content: data.content,
          media_type: 'text/markdown',
          severity: data.severity,
        },
      });
      onClose();
      formHook.reset();
    } catch (error) {
      console.error('Failed to create message:', error);
      // If fresh login is required, show fresh login modal
      if (freshLogin?.isFreshLoginRequired(error)) {
        freshLogin.showFreshLoginModal(async () => {
          try {
            // Retry the create operation after fresh login
            await createMessage.mutateAsync({
              message: {
                content: data.content,
                media_type: 'text/markdown',
                severity: data.severity,
              },
            });
            onClose();
            formHook.reset();
          } catch (retryError) {
            console.error(
              'Failed to create message after fresh login:',
              retryError,
            );
          }
        });
      }
    }
  };

  const handleClose = () => {
    onClose();
    formHook.reset();
    setActiveTabKey('write');
  };

  return (
    <Modal
      variant={ModalVariant.large}
      title="Create new message"
      isOpen={isOpen}
      onClose={handleClose}
      actions={[
        <Button
          key="create"
          variant="primary"
          onClick={handleSubmit(onSubmit)}
          isLoading={createMessage.isLoading}
          isDisabled={createMessage.isLoading || !formState.isValid}
        >
          Create Message
        </Button>,
        <Button key="cancel" variant="link" onClick={handleClose}>
          Cancel
        </Button>,
      ]}
    >
      <Form>
        <FormGroup label="Severity" fieldId="severity" isRequired>
          <Controller
            name="severity"
            control={control}
            rules={{required: 'Severity is required'}}
            render={({field}) => (
              <FormSelect
                {...field}
                id="severity"
                validated={formState.errors.severity ? 'error' : 'default'}
              >
                <FormSelectOption value="info" label="Normal (Info)" />
                <FormSelectOption value="warning" label="Warning" />
                <FormSelectOption value="error" label="Error" />
              </FormSelect>
            )}
          />
        </FormGroup>

        <FormGroup label="Message" fieldId="message-content" isRequired>
          <Tabs
            activeKey={activeTabKey}
            onSelect={(_, tabIndex) => setActiveTabKey(tabIndex)}
          >
            <Tab eventKey="write" title={<TabTitleText>Write</TabTitleText>}>
              <div>
                {/* Markdown Toolbar */}
                <Toolbar
                  style={{padding: '0.5rem', backgroundColor: '#f5f5f5'}}
                >
                  <ToolbarContent>
                    <ToolbarGroup>
                      <ToolbarItem>
                        <Button
                          variant="plain"
                          aria-label="Bold"
                          onClick={() => insertMarkdown('**', '**')}
                        >
                          <BoldIcon />
                        </Button>
                      </ToolbarItem>
                      <ToolbarItem>
                        <Button
                          variant="plain"
                          aria-label="Italic"
                          onClick={() => insertMarkdown('_', '_')}
                        >
                          <ItalicIcon />
                        </Button>
                      </ToolbarItem>
                      <ToolbarItem>
                        <Button
                          variant="plain"
                          aria-label="Quote"
                          onClick={() => insertMarkdown('\n> ', '')}
                        >
                          <QuoteLeftIcon />
                        </Button>
                      </ToolbarItem>
                      <ToolbarItem>
                        <Button
                          variant="plain"
                          aria-label="Code"
                          onClick={() => insertMarkdown('`', '`')}
                        >
                          <CodeIcon />
                        </Button>
                      </ToolbarItem>
                      <ToolbarItem>
                        <Button
                          variant="plain"
                          aria-label="Link"
                          onClick={() => insertMarkdown('[', '](url)')}
                        >
                          <LinkIcon />
                        </Button>
                      </ToolbarItem>
                      <ToolbarItem>
                        <Button
                          variant="plain"
                          aria-label="List"
                          onClick={() => insertMarkdown('\n- ', '')}
                        >
                          <ListIcon />
                        </Button>
                      </ToolbarItem>
                    </ToolbarGroup>
                  </ToolbarContent>
                </Toolbar>

                {/* Content TextArea */}
                <Controller
                  name="content"
                  control={control}
                  rules={{required: 'Message content is required'}}
                  render={({field}) => (
                    <TextArea
                      {...field}
                      id="message-content"
                      placeholder="Enter your message here..."
                      rows={10}
                      validated={formState.errors.content ? 'error' : 'default'}
                      style={{fontFamily: 'monospace'}}
                    />
                  )}
                />
              </div>
            </Tab>

            <Tab
              eventKey="preview"
              title={<TabTitleText>Preview</TabTitleText>}
            >
              <Card>
                <CardBody>
                  {currentContent ? (
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
                              rel={
                                isExternal ? 'noopener noreferrer' : undefined
                              }
                            >
                              {children}
                            </a>
                          );
                        },
                      }}
                    >
                      {currentContent}
                    </Markdown>
                  ) : (
                    <em>No content to preview</em>
                  )}
                </CardBody>
              </Card>
            </Tab>
          </Tabs>
        </FormGroup>
      </Form>
    </Modal>
  );
}
