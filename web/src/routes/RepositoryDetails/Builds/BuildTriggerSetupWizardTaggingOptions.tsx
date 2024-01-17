import {
  Title,
  FormGroup,
  Checkbox,
  List,
  ListItem,
  TextInput,
  Button,
  Form,
} from '@patternfly/react-core';
import {TrashIcon} from '@patternfly/react-icons';
import {useState} from 'react';
import Conditional from 'src/components/empty/Conditional';

export default function TaggingOptionsStep(props: TaggingOptionsStepProps) {
  const {
    tagWithBranchOrTag,
    setTagWithBranchOrTag,
    addLatestTag,
    setAddLatestTag,
    tagTemplates,
    setTagTemplates,
  } = props;
  const [tagTemplate, setTagTemplate] = useState('');
  const addTagTemplate = () => {
    if (!tagTemplates.includes(tagTemplate)) {
      setTagTemplates([...tagTemplates, tagTemplate]);
    }
    setTagTemplate('');
  };

  const removeTagTemplate = (template) => {
    setTagTemplates(tagTemplates.filter((t) => t !== template));
  };
  return (
    <>
      <Title headingLevel="h2">Configure Tagging</Title>
      <br />
      <Form>
        <Title headingLevel="h5">Confirm basic tagging options</Title>
        <FormGroup isRequired fieldId="tagging-options">
          <Checkbox
            label="Tag manifest with the branch or tag name"
            description="Tags the built manifest the name of the branch or tag for the git commit."
            id="tag-manifest-with-branch-or-tag-name-checkbox"
            name="tag-manifest-with-branch-or-tag-name-checkbox"
            isChecked={tagWithBranchOrTag}
            onChange={() => setTagWithBranchOrTag(!tagWithBranchOrTag)}
          />
          <br />
          <Checkbox
            label={
              <>
                Add <code>latest</code> tag if on default branch
              </>
            }
            description={
              <>
                Tags the built manifest with <code>latest</code> if the build
                occurred on the default branch for the repository.
              </>
            }
            id="tag-with-latest-checkbox"
            name="tag-with-latest-checkbox"
            isChecked={addLatestTag}
            onChange={() => setAddLatestTag(!addLatestTag)}
          />
        </FormGroup>
        <Title headingLevel="h5">Add custom tagging templates</Title>
        <Conditional if={tagTemplates.length === 0}>
          No tag templates defined.
        </Conditional>
        <Conditional if={tagTemplates.length > 0}>
          <List>
            {tagTemplates.map((template) => (
              <ListItem id={template} key={template}>
                {template}{' '}
                <a
                  onClick={() => removeTagTemplate(template)}
                  style={{color: 'black'}}
                >
                  <TrashIcon />
                </a>
              </ListItem>
            ))}
          </List>
        </Conditional>
        <div>
          <span>Enter a tag template:</span>
          <span style={{width: '30em'}}>
            <TextInput
              placeholder="${commit_info.short_sha}"
              id="tag-template"
              name="tag-template"
              value={tagTemplate}
              onChange={(_, val) => setTagTemplate(val)}
            />
          </span>
          <span>
            <Button
              variant="secondary"
              onClick={addTagTemplate}
              isDisabled={tagTemplate === ''}
            >
              Add template
            </Button>
          </span>
        </div>
      </Form>
      <br />
      <p>
        By default, all built manifests will be tagged with the name of the
        branch or tag in which the commit occurred.
      </p>
      <p>
        To modify this default, as well as the default to add the{' '}
        <code>latest</code> tag, change the corresponding options above
      </p>
      <br />
      <p>
        Need more control over how the built manifest is tagged? Add one or more
        custom tag templates.
      </p>
      <p>
        For example, if you want all built manifests to be tagged with the
        commit&apos;s short SHA, add a template of{' '}
        <code>$&#123;commit_info.short_sha&#125;</code>.
      </p>
      <p>
        As another example, if you want on those manifests committed to a{' '}
        <b>branch</b> to be tagged with the branch name, you can add a template
        of <code>$&#123;parsed_ref.branch&#125;</code>.
      </p>
      <p>
        A full reference of for these templates can be found in the{' '}
        <a
          href="https://access.redhat.com/solutions/7033393"
          target="_blank"
          rel="noreferrer"
        >
          tag template documentation
        </a>
        .
      </p>
    </>
  );
}

interface TaggingOptionsStepProps {
  tagWithBranchOrTag: boolean;
  setTagWithBranchOrTag: (tagWithBranchOrTag: boolean) => void;
  addLatestTag: boolean;
  setAddLatestTag: (addLatestTag: boolean) => void;
  tagTemplates: string[];
  setTagTemplates: (tagTemplates: string[]) => void;
}
