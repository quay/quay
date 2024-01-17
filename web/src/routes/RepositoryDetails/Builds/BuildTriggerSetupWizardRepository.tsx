import {
  FormGroup,
  TextInput,
  FormHelperText,
  HelperText,
  HelperTextItem,
  Form,
} from '@patternfly/react-core';
import {useState} from 'react';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

export default function RepositoryStep(props: RepositoryStepProps) {
  const quayConfig = useQuayConfig();
  const handleEnterRepoUrlOnChange = (_, value: string) => {
    const isValid = /^(((http|https):\/\/)(.+)|\w+@(.+):(.+))$/.test(value);
    props.setRepoUrl(value);
    props.setRepoUrlValid(isValid);
  };
  return (
    <>
      <Form>
        <FormGroup
          label="Enter repository"
          labelInfo="Please enter the HTTP or SSH style URL used to clone your git repository"
          isRequired
          fieldId="select-repository"
        >
          <TextInput
            isRequired
            type="url"
            id="repo-url"
            name="repo-url"
            value={props.repoUrl}
            placeholder="git@example.com:namespace/repository.git"
            onChange={handleEnterRepoUrlOnChange}
          />
          <FormHelperText>
            <HelperText>
              <HelperTextItem
                variant={props.repoUrlValid ? 'default' : 'error'}
              >
                {props.repoUrl !== '' &&
                  !props.repoUrlValid &&
                  'Must be a valid URL'}
              </HelperTextItem>
            </HelperText>
          </FormHelperText>
        </FormGroup>
      </Form>
      <br />
      <p>
        Custom git triggers support any externally accessible git repository,
        via either the normal git protocol or HTTP.
      </p>
      <p>
        <b>
          {' '}
          It is the responsibility of the git repository to invoke a webhook to
          tell {quayConfig?.config?.REGISTRY_TITLE_SHORT} that a commit has been
          added.
        </b>
      </p>
    </>
  );
}

interface RepositoryStepProps {
  repoUrl: string;
  setRepoUrl: (repoUrl: string) => void;
  repoUrlValid: boolean;
  setRepoUrlValid: (repoUrlValid: boolean) => void;
}
