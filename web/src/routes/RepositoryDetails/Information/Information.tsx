import {
  Button,
  Card,
  CardBody,
  CardTitle,
  ClipboardCopy,
  CodeBlock,
  CodeBlockAction,
  CodeBlockCode,
  ClipboardCopyButton,
  Grid,
  GridItem,
  PageSection,
  Content,
  TextArea,
  ContentVariants,
} from '@patternfly/react-core';
import {Table, Th, Td} from '@patternfly/react-table';
import {useEffect, useState} from 'react';
import {useMutation, useQueryClient} from '@tanstack/react-query';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useQuayState} from 'src/hooks/UseQuayState';
import {RepositoryDetails} from 'src/resources/RepositoryResource';
import axios from 'src/libs/axios';
import {AlertVariant, useUI} from 'src/contexts/UIContext';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import React from 'react';
import ActivityHeatmap from 'src/components/ActivityHeatmap/ActivityHeatmap';
import RecentRepoBuilds from './RecentRepoBuilds';
import './Information.css';

interface InformationProps {
  organization: string;
  repository: string;
  repoDetails: RepositoryDetails;
}

const MarkdownCodeBlock: React.FunctionComponent<{code: string}> = (props) => {
  const [copied, setCopied] = React.useState(false);

  const clipboardCopyFunc = (_event: React.MouseEvent, text: string) => {
    navigator.clipboard.writeText(text.toString());
  };

  const onClick = (event: React.MouseEvent, text: string) => {
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

async function updateRepositoryDescription(
  org: string,
  repo: string,
  description: string,
) {
  const response = await axios.put(`/api/v1/repository/${org}/${repo}`, {
    description,
  });
  return response.data;
}

export default function Information(props: InformationProps) {
  const {organization, repository, repoDetails} = props;
  const config = useQuayConfig();
  const {inReadOnlyMode} = useQuayState();
  const {addAlert} = useUI();
  const queryClient = useQueryClient();

  const [description, setDescription] = useState(
    repoDetails?.description || '',
  );
  const [isEditing, setIsEditing] = useState(false);

  // Sync description state with repoDetails when it changes
  useEffect(() => {
    setDescription(repoDetails?.description || '');
  }, [repoDetails?.description]);

  const updateDescriptionMutation = useMutation(
    async (newDescription: string) => {
      return await updateRepositoryDescription(
        organization,
        repository,
        newDescription,
      );
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries([
          'repodetails',
          organization,
          repository,
        ]);
        setIsEditing(false);
        addAlert({
          variant: AlertVariant.Success,
          title: 'Repository description updated successfully',
        });
      },
      onError: (error) => {
        addAlert({
          variant: AlertVariant.Failure,
          title: 'Failed to update repository description',
        });
        console.error('Error updating description:', error);
      },
    },
  );

  const handleDescriptionChange = (value: string) => {
    setDescription(value);
  };

  const handleSaveDescription = () => {
    updateDescriptionMutation.mutate(description);
  };

  const handleCancelEdit = () => {
    setDescription(repoDetails?.description || '');
    setIsEditing(false);
  };

  const serverHostname = config?.config?.SERVER_HOSTNAME || 'quay.io';
  const podmanPullCommand = `podman pull ${serverHostname}/${organization}/${repository}`;
  const dockerPullCommand = `docker pull ${serverHostname}/${organization}/${repository}`;

  return (
    <PageSection hasBodyWrapper={false}>
      <Grid hasGutter>
        {/* Repository Activity Heatmap */}
        <GridItem span={12} md={5}>
          <Card>
            <CardTitle>Repository Activity</CardTitle>
            <CardBody>
              {repoDetails?.stats && repoDetails.stats.length > 0 ? (
                <ActivityHeatmap data={repoDetails.stats} itemName="action" />
              ) : (
                <Content style={{textAlign: 'center', padding: '2rem'}}>
                  <Content component={ContentVariants.small}>
                    No activity data available
                  </Content>
                </Content>
              )}
            </CardBody>
          </Card>
        </GridItem>

        {/* Right Column: Recent Builds + Pull Commands */}
        <GridItem span={12} md={7}>
          {/* Recent Repo Builds - only if BUILD_SUPPORT is enabled */}
          {config?.features?.BUILD_SUPPORT && (
            <RecentRepoBuilds
              organization={organization}
              repository={repository}
              canWrite={repoDetails?.can_write || false}
              canAdmin={repoDetails?.can_admin || false}
            />
          )}

          {/* Pull Commands - add margin-top if builds section is shown */}
          <Card
            style={
              config?.features?.BUILD_SUPPORT ? {marginTop: '1rem'} : undefined
            }
          >
            <CardTitle>Pull Commands</CardTitle>
            <CardBody>
              <Grid hasGutter>
                <GridItem span={12}>
                  <Content>
                    <Content component={ContentVariants.small}>
                      Pull this container with the following Podman command:
                    </Content>
                  </Content>
                  <ClipboardCopy isReadOnly hoverTip="Copy" clickTip="Copied">
                    {podmanPullCommand}
                  </ClipboardCopy>
                </GridItem>
                <GridItem span={12}>
                  <Content>
                    <Content component={ContentVariants.small}>
                      Pull this container with the following Docker command:
                    </Content>
                  </Content>
                  <ClipboardCopy isReadOnly hoverTip="Copy" clickTip="Copied">
                    {dockerPullCommand}
                  </ClipboardCopy>
                </GridItem>
              </Grid>
            </CardBody>
          </Card>
        </GridItem>

        {/* Repository Description */}
        <GridItem span={12}>
          <Card>
            <CardTitle>Description</CardTitle>
            <CardBody>
              {!isEditing && (
                <>
                  {description ? (
                    <Content>
                      <Markdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          code({children}) {
                            const childText =
                              typeof children === 'string'
                                ? children
                                : String(children);
                            // Detect inline code by checking for newlines
                            // react-markdown v10.x doesn't reliably pass the inline prop
                            const isInline = !childText.includes('\n');
                            return isInline ? (
                              <code className="inline-code">{children}</code>
                            ) : (
                              <MarkdownCodeBlock code={childText} />
                            );
                          },
                          table: ({children}) => (
                            <Table borders={true} variant={'compact'}>
                              {children}
                            </Table>
                          ),
                          th: ({children}) => (
                            <Th className="markdown-table-header">
                              {children}
                            </Th>
                          ),
                          td: ({children}) => (
                            <Td className="markdown-table-cell">{children}</Td>
                          ),
                        }}
                      >
                        {description}
                      </Markdown>
                    </Content>
                  ) : (
                    <Content>
                      <Content component={ContentVariants.p}>
                        No description provided
                      </Content>
                    </Content>
                  )}
                  {repoDetails?.can_write && !inReadOnlyMode && (
                    <Content>
                      <Content
                        component={ContentVariants.a}
                        onClick={() => setIsEditing(true)}
                        style={{cursor: 'pointer', marginTop: '1rem'}}
                      >
                        Edit description
                      </Content>
                    </Content>
                  )}
                </>
              )}
              {isEditing && (
                <>
                  <Content>
                    <Content
                      component={ContentVariants.small}
                      style={{marginBottom: '0.5rem'}}
                    >
                      Supports Markdown formatting
                    </Content>
                  </Content>
                  <TextArea
                    value={description}
                    onChange={(_event, value) => handleDescriptionChange(value)}
                    rows={5}
                    aria-label="Repository description"
                    placeholder="Enter repository description..."
                  />
                  <div style={{marginTop: '1rem'}}>
                    <Button
                      variant="primary"
                      onClick={handleSaveDescription}
                      isLoading={updateDescriptionMutation.isLoading}
                      isDisabled={updateDescriptionMutation.isLoading}
                    >
                      Save
                    </Button>{' '}
                    <Button
                      variant="link"
                      onClick={handleCancelEdit}
                      isDisabled={updateDescriptionMutation.isLoading}
                    >
                      Cancel
                    </Button>
                  </div>
                </>
              )}
            </CardBody>
          </Card>
        </GridItem>
      </Grid>
    </PageSection>
  );
}
