import {Alert, Radio, Spinner, TextInput, Title} from '@patternfly/react-core';
import {CodeBranchIcon, TagIcon} from '@patternfly/react-icons';
import RegexMatchView, {RegexMatchItem} from 'src/components/RegexMatchView';
import Conditional from 'src/components/empty/Conditional';
import {useSourceRefs} from 'src/hooks/UseBuildTriggers';
import {isNullOrUndefined} from 'src/libs/utils';
import {GitNamespace} from 'src/resources/BuildResource';

export default function TriggerOptions(props: TriggerOptions) {
  const {
    org,
    repo,
    triggerUuid,
    repoUrl,
    gitNamespace,
    branchTagFilter,
    setBranchTagFilter,
    hasBranchTagFilter,
    setHasBranchTagFilter,
  } = props;

  const {refs, isLoading, error, isError} = useSourceRefs(
    org,
    repo,
    triggerUuid,
    repoUrl,
  );

  if (isLoading) {
    return <Spinner />;
  }

  if (isError) {
    return <Alert variant="danger" title={error.toString()} />;
  }

  const regexItems: RegexMatchItem[] = refs.map((ref) => {
    const kind = ref.kind == 'branch' ? 'heads' : 'tags';
    const icon = ref.kind == 'branch' ? <CodeBranchIcon /> : <TagIcon />;
    return {
      value: `${kind}/${ref.name}`,
      icon: icon,
      title: ref.name,
    };
  });

  return (
    <>
      <Title headingLevel="h5">
        Configure trigger options for{' '}
        <Conditional if={!isNullOrUndefined(gitNamespace.avatar_url)}>
          <img
            style={{height: '1em', width: '1em', marginRight: '1em'}}
            src={gitNamespace.avatar_url}
          />
        </Conditional>
        {gitNamespace.title}
      </Title>
      <Radio
        label="Trigger for all branches and tags (default)"
        description="Build a container image for each commit across all branches and tags"
        id="trigger-on-all-branches-and-tags-checkbox"
        name="trigger-on-all-branches-and-tags-checkbox"
        isChecked={!hasBranchTagFilter}
        checked={!hasBranchTagFilter}
        onChange={() => setHasBranchTagFilter(false)}
      />
      <br />
      <Radio
        label="Trigger only on branches and tags matching a regular expression"
        description="Only build container images for a subset of branches and/or tags"
        id="branch-tag-filter-checkbox"
        name="branch-tag-filter-checkbox"
        isChecked={hasBranchTagFilter}
        checked={hasBranchTagFilter}
        onChange={() => setHasBranchTagFilter(true)}
      />
      <Conditional if={hasBranchTagFilter}>
        <TextInput
          isRequired
          type="url"
          id="branch-tag-filter"
          name="branch-tag-filter"
          value={branchTagFilter}
          onChange={(_, value) => setBranchTagFilter(value)}
        />
        Examples: heads/master, tags/tagname, heads/.+
        <Conditional
          if={!isNullOrUndefined(branchTagFilter) && branchTagFilter.length > 0}
        >
          <RegexMatchView regex={branchTagFilter} items={regexItems} />
        </Conditional>
      </Conditional>
      <br />
      <br />
      <p>
        Do you want to build a new container image for commits across all
        branches and tags, or limit to a subset?
      </p>
      <p>
        For example, if you use release branches instead of <code>master</code>{' '}
        for building versions of your software, you can configure the trigger to
        only build images for these branches.
      </p>
      <p>
        All images built will be tagged with the name of the branch or tag whose
        change invoked the trigger
      </p>
    </>
  );
}

interface TriggerOptions {
  org: string;
  repo: string;
  triggerUuid: string;
  gitNamespace: GitNamespace;
  repoUrl: string;
  branchTagFilter: string;
  setBranchTagFilter: (branchTagFilter: string) => void;
  hasBranchTagFilter: boolean;
  setHasBranchTagFilter: (hasBranchTagFilter: boolean) => void;
}
