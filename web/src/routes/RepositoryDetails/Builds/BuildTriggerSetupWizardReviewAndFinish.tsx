import {
  Button,
  DescriptionList,
  DescriptionListDescription,
  DescriptionListGroup,
  DescriptionListTerm,
  Title,
} from '@patternfly/react-core';
import {PlusCircleIcon} from '@patternfly/react-icons';
import Conditional from 'src/components/empty/Conditional';
import {isNullOrUndefined} from 'src/libs/utils';

export default function ReviewAndFinishProps(props: ReviewAndFinishProps) {
  const {
    repoUrl,
    tagTemplates,
    tagWithBranchOrTag,
    addLatestTag,
    dockerfilePath,
    contextPath,
    robotAccount,
  } = props;
  return (
    <>
      <Title headingLevel="h1" size="lg">
        Review and Finish
      </Title>
      <DescriptionList>
        <DescriptionListGroup>
          <DescriptionListTerm>Repository URL</DescriptionListTerm>
          <DescriptionListDescription id="repo-url">
            {repoUrl}
          </DescriptionListDescription>
        </DescriptionListGroup>
        <Conditional if={tagTemplates?.length > 0}>
          <DescriptionListGroup>
            <DescriptionListTerm>Tag Templates</DescriptionListTerm>
            <DescriptionListDescription id="tag-templates">
              {tagTemplates.map((template) => (
                <div key={template}>{template}</div>
              ))}
            </DescriptionListDescription>
          </DescriptionListGroup>
        </Conditional>
        <DescriptionListGroup>
          <DescriptionListTerm>Tag With Branch or Tag Name</DescriptionListTerm>
          <DescriptionListDescription id="tag-with-branch-or-tag">
            {tagWithBranchOrTag ? 'enabled' : 'disabled'}
          </DescriptionListDescription>
        </DescriptionListGroup>
        <DescriptionListGroup>
          <DescriptionListTerm>
            Add The <code>latest</code> Tag
          </DescriptionListTerm>
          <DescriptionListDescription id="tag-with-latest">
            {addLatestTag ? 'enabled' : 'disabled'}
          </DescriptionListDescription>
        </DescriptionListGroup>
        <DescriptionListGroup>
          <DescriptionListTerm>Path to Dockerfile</DescriptionListTerm>
          <DescriptionListDescription id="dockerfile-path">
            {dockerfilePath}
          </DescriptionListDescription>
        </DescriptionListGroup>
        <DescriptionListGroup>
          <DescriptionListTerm>Path to Context</DescriptionListTerm>
          <DescriptionListDescription id="context-path">
            {contextPath}
          </DescriptionListDescription>
        </DescriptionListGroup>
        <Conditional if={!isNullOrUndefined(robotAccount)}>
          <DescriptionListGroup>
            <DescriptionListTerm>Robot Account</DescriptionListTerm>
            <DescriptionListDescription id="robot-account">
              {robotAccount}
            </DescriptionListDescription>
          </DescriptionListGroup>
        </Conditional>
      </DescriptionList>
    </>
  );
}

interface ReviewAndFinishProps {
  repoUrl: string;
  tagTemplates: string[];
  tagWithBranchOrTag: boolean;
  addLatestTag: boolean;
  dockerfilePath: string;
  contextPath: string;
  robotAccount: string;
}
