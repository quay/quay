import {
  Form,
  FormGroup,
  FormHelperText,
  HelperText,
  HelperTextItem,
  TextInput,
} from '@patternfly/react-core';
import {useState} from 'react';
import Conditional from 'src/components/empty/Conditional';

export default function ContextStep(props: ContextStepProps) {
  const [error, setError] = useState<string>('');
  const onChange = (_, value: string) => {
    if (value.length === 0 || value.slice(0, 1)[0] !== '/') {
      setError('Path is an invalid context.');
      props.setContextPathValid(false);
    } else {
      setError('');
      props.setContextPathValid(true);
    }
    props.setContextPath(value);
  };
  return (
    <>
      <Form>
        <FormGroup
          label="Select Context"
          labelInfo="Please select the context for the Docker build"
          isRequired
          fieldId="select-context"
        >
          <Conditional if={props.isCustomGit}>
            <TextInput
              isRequired
              type="text"
              id="context-path"
              name="context-path"
              value={props.contextPath}
              placeholder="/"
              onChange={onChange}
            />
            <FormHelperText>
              <HelperText>
                <HelperTextItem variant={error !== '' ? 'error' : 'default'}>
                  {error}
                </HelperTextItem>
              </HelperText>
            </FormHelperText>
          </Conditional>
        </FormGroup>
      </Form>
      <br />
      <p>Please select a Docker context.</p>
      <p>
        The build context directory is the path of the directory containing the
        Dockerfile and any other files to be made available when the build is
        triggered.
      </p>
      <p>
        If the Dockerfile is located at the root of the git repository, enter{' '}
        <code>/</code> as the build context directory.
      </p>
    </>
  );
}

interface ContextStepProps {
  contextPath: string;
  setContextPath: (contextPath: string) => void;
  isCustomGit: boolean;
  setContextPathValid: (contextPathValid: boolean) => void;
}
