import {
  Alert,
  Form,
  FormGroup,
  FormHelperText,
  HelperText,
  HelperTextItem,
  MenuToggle,
  MenuToggleElement,
  Select,
  SelectList,
  SelectOption,
  Spinner,
  TextInput,
  TextInputGroup,
  TextInputGroupMain,
  TextInputGroupUtilities,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import TypeAheadSelect from 'src/components/TypeAheadSelect';
import Conditional from 'src/components/empty/Conditional';
import {isNullOrUndefined} from 'src/libs/utils';
import {analyzeBuildTrigger} from 'src/resources/BuildResource';

export default function DockerfileStep(props: DockerfileStepProps) {
  const {
    org,
    repo,
    triggerUuid,
    buildSource,
    isCustomGit,
    setDockerPathValid,
    setDockerfilePath,
    dockerfilePath,
    dockerfilePaths: initialDockerfilePaths,
    isLoading,
    isError,
    error: sourceDirsError,
  } = props;
  const [error, setError] = useState<string>('');
  const [warning, setWarning] = useState<string>('');
  const [analyzeError, setAnalyzeError] = useState<string>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState<boolean>(false);

  useEffect(() => {
    const delay = setTimeout(async () => {
      setError('');
      setWarning('');
      setDockerPathValid(false);
      setAnalyzeError(null);
      if (dockerfilePath != null && dockerfilePath != '') {
        if (dockerfilePath.split('/').splice(-1)[0] == '') {
          setError('Dockerfile path must end with a file, e.g. "Dockerfile"');
        } else if (
          dockerfilePath == null ||
          dockerfilePath.length == 0 ||
          dockerfilePath.slice(0, 1)[0] !== '/'
        ) {
          setError(
            'Path entered for folder containing Dockerfile is invalid: Must start with a "/".',
          );
        } else if (!isCustomGit) {
          try {
            setLoadingAnalysis(true);
            const analysis = await analyzeBuildTrigger(
              org,
              repo,
              triggerUuid,
              buildSource,
              null,
              dockerfilePath,
            );
            if (analysis.status === 'warning') {
              setDockerPathValid(true);
              setWarning(analysis.message);
            } else if (analysis.status === 'error') {
              setDockerPathValid(false);
              setError(analysis.message);
            } else {
              setDockerPathValid(true);
            }
            setLoadingAnalysis(false);
          } catch (error) {
            setLoadingAnalysis(false);
            const message =
              error?.response?.data?.error_message || error.toString();
            setAnalyzeError(message);
          }
        } else {
          setDockerPathValid(true);
        }
      }
    }, 1000);
    return () => clearTimeout(delay);
  }, [dockerfilePath]);

  if (!isCustomGit && isLoading) {
    return <Spinner />;
  }

  if (isError || !isNullOrUndefined(analyzeError)) {
    const message = isError ? sourceDirsError.toString() : analyzeError;
    return <Alert variant="danger" title={message} />;
  }

  return (
    <>
      <Form>
        <FormGroup
          label="Select Dockerfile"
          labelInfo="Please select the location of the Dockerfile to build when this trigger is invoked"
          isRequired
          fieldId="select-dockerfile"
        >
          <Conditional if={isCustomGit}>
            <TextInput
              isRequired
              type="text"
              id="dockerfile-path"
              name="dockerfile-path"
              value={dockerfilePath}
              placeholder="/Dockerfile"
              onChange={(_, value) => setDockerfilePath(value)}
            />
          </Conditional>
          <Conditional
            if={!isCustomGit && !isNullOrUndefined(initialDockerfilePaths)}
          >
            <TypeAheadSelect
              value={dockerfilePath}
              onChange={(value) => setDockerfilePath(value)}
              initialSelectOptions={initialDockerfilePaths?.map(
                (path, index) => {
                  return {
                    key: path,
                    onClick: () => setDockerfilePath(path),
                    id: `dockerfile-path-option-${index}`,
                    value: path,
                  };
                },
              )}
            />
          </Conditional>
          <FormHelperText>
            <HelperText>
              <Conditional if={loadingAnalysis}>
                <HelperTextItem variant="default">
                  <Spinner size="sm" />
                </HelperTextItem>
              </Conditional>
              <Conditional if={error !== ''}>
                <HelperTextItem variant="error">{error}</HelperTextItem>
              </Conditional>
              <Conditional if={warning !== ''}>
                <HelperTextItem variant="warning">{warning}</HelperTextItem>
              </Conditional>
            </HelperText>
          </FormHelperText>
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
  org: string;
  repo: string;
  triggerUuid: string;
  buildSource: string;
  dockerfilePath: string;
  setDockerfilePath: (dockerfilePath: string) => void;
  isCustomGit: boolean;
  setDockerPathValid: (dockerPathValid: boolean) => void;
  dockerfilePaths: string[];
  isLoading: boolean;
  isError: boolean;
  contexts: Map<string, string[]>;
  error: unknown;
}
