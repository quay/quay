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

export default function DockerfileStep(props: DockerfileStepProps) {
  const [error, setError] = useState<string>('');
  const onChange = (_, value: string) => {
    if (value.split('/').splice(-1)[0] == '') {
      setError('Dockerfile path must end with a file, e.g. "Dockerfile"');
      props.setDockerPathValid(false);
    } else if (
      value == null ||
      value.length == 0 ||
      value.slice(0, 1)[0] !== '/'
    ) {
      setError(
        'Path entered for folder containing Dockerfile is invalid: Must start with a "/".',
      );
      props.setDockerPathValid(false);
    } else {
      setError('');
      props.setDockerPathValid(true);
    }
    props.setDockerfilePath(value);
  };
  return (
    <>
      <Form>
        <FormGroup
          label="Select Dockerfile"
          labelInfo="Please select the location of the Dockerfile to build when this trigger is invoked"
          isRequired
          fieldId="select-dockerfile"
        >
          <Conditional if={props.isCustomGit}>
            <TextInput
              isRequired
              type="text"
              id="dockerfile-path"
              name="dockerfile-path"
              value={props.dockerfilePath}
              placeholder="/Dockerfile"
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
      <p>Please select the location containing the Dockerfile to be built.</p>
      <p>
        The Dockerfile path starts with the context and ends with the path to
        the Dockefile that you would like to build.
      </p>
      <p>
        If the Dockerfile is located at the root of the git repository and named
        Dockerfile, enter <code>/Dockerfile</code> as the Dockerfile path.
      </p>
    </>
  );
}

interface DockerfileStepProps {
  dockerfilePath: string;
  setDockerfilePath: (dockerfilePath: string) => void;
  isCustomGit: boolean;
  setDockerPathValid: (dockerPathValid: boolean) => void;
}
