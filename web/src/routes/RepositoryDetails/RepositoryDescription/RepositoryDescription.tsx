import React, {useEffect, useState} from 'react';
import Markdown from 'react-markdown';
import {
  List,
  ListComponent,
  ListItem,
  OrderType,
  PageSection,
  Text,
  PageSectionVariants,
  TextVariants,
  Title,
  Button,
  FlexItem,
  Flex,
  Split,
  SplitItem,
  CodeBlock,
  CodeBlockCode,
} from '@patternfly/react-core';
import remarkGfm from 'remark-gfm';

import './RepositoryDescription.css';
import {EditIcon, TaskIcon} from '@patternfly/react-icons';
import {DescriptionEditor} from './DescriptionEditor';
import {useUpdateRepositoryDescription} from 'src/hooks/useUpdateRepositoryDescription';
import Conditional from 'src/components/empty/Conditional';
import Empty from 'src/components/empty/Empty';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {LoadingPage} from 'src/components/LoadingPage';
import {AlertVariant} from 'src/atoms/AlertState';
import {useAlerts} from 'src/hooks/UseAlerts';

const markdownComponents = {
  h1: ({node, ...props}) => <Title headingLevel="h1" {...props} />,
  h2: ({node, ...props}) => <Title headingLevel="h2" {...props} />,
  h3: ({node, ...props}) => <Title headingLevel="h3" {...props} />,
  h4: ({node, ...props}) => <Title headingLevel="h4" {...props} />,
  p: ({node, ...props}) => <Text component={TextVariants.p} {...props} />,
  ul: ({node, ...props}) => <List {...props} />,
  li: ({node, children, ...props}) => (
    <ListItem {...props}> {children} </ListItem>
  ),
  ol: ({node, ...props}) => (
    <List component={ListComponent.ol} type={OrderType.number} {...props} />
  ),
  pre: ({node, children, ...props}) => (
    <CodeBlock {...props}>
      <CodeBlockCode>{children}</CodeBlockCode>
    </CodeBlock>
  ),
};

interface RepositoryDescriptionProps {
  description: string;
  canEdit: boolean;
  org: string;
  repo: string;
  isLoading: boolean;
}

export default function RepositoryDescription(
  props: RepositoryDescriptionProps,
) {
  const config = useQuayConfig();
  const {addAlert} = useAlerts();
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const {
    setRepoDescription,
    errorSetRepoDescription,
    successSetRepoDescription,
  } = useUpdateRepositoryDescription(props.org, props.repo);

  const onEdit = () => {
    setIsEditing(true);
  };

  const onCancel = () => {
    setIsEditing(false);
  };

  const onSave = (description: string) => {
    setIsEditing(false);
    setRepoDescription(description);
  };

  useEffect(() => {
    if (errorSetRepoDescription) {
      addAlert({
        variant: AlertVariant.Failure,
        title: `Unable to update description for: ${props.org}/${props.repo}`,
      });
    }
  }, [errorSetRepoDescription]);

  useEffect(() => {
    if (successSetRepoDescription) {
      addAlert({
        variant: AlertVariant.Success,
        title: `Description updated successfully for: ${props.org}/${props.repo}`,
      });
    }
  }, [successSetRepoDescription]);

  if (props.isLoading) {
    return <LoadingPage />;
  }

  return (
    <PageSection variant={PageSectionVariants.light}>
      <Conditional if={!props.description && !isEditing}>
        <Empty
          icon={TaskIcon}
          title={'Repository description not found'}
          body={
            'create a description for this repository to help others understand its purpose and contents. (Markdown supported)'
          }
          button={
            <Conditional if={config?.registry_state !== 'readonly'}>
              <Button
                variant="primary"
                ouiaId="Add description"
                onClick={onEdit}
              >
                Add description
              </Button>
            </Conditional>
          }
        />
      </Conditional>
      <Flex direction={{default: 'column'}}>
        <Conditional
          if={
            props.canEdit &&
            !isEditing &&
            props.description &&
            config.registry_state !== 'readonly'
          }
        >
          <FlexItem>
            <Split>
              <SplitItem isFilled></SplitItem>
              <SplitItem>
                <Button
                  variant="primary"
                  icon={<EditIcon />}
                  ouiaId="edit-description"
                  onClick={onEdit}
                >
                  Edit
                </Button>
              </SplitItem>
            </Split>
          </FlexItem>
        </Conditional>
        <FlexItem>
          {isEditing ? (
            <DescriptionEditor
              description={props.description}
              onSave={onSave}
              onCancel={onCancel}
            />
          ) : (
            <Markdown
              className={'description'}
              remarkPlugins={[remarkGfm]}
              components={markdownComponents}
            >
              {props.description}
            </Markdown>
          )}
        </FlexItem>
      </Flex>
    </PageSection>
  );
}
