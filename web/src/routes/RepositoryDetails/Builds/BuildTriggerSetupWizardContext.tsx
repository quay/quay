import {
  Alert,
  Form,
  FormGroup,
  FormHelperText,
  HelperText,
  HelperTextItem,
  Spinner,
  TextInput,
} from '@patternfly/react-core';
import {useEffect, useState} from 'react';
import TypeAheadSelect from 'src/components/TypeAheadSelect';
import Conditional from 'src/components/empty/Conditional';
import {isNullOrUndefined} from 'src/libs/utils';
import {analyzeBuildTrigger} from 'src/resources/BuildResource';

export default function ContextStep(props: ContextStepProps) {
  const {
    org,
    repo,
    triggerUuid,
    buildSource,
    isCustomGit,
    contextPath,
    setContextPath,
    setContextPathValid,
    dockerfilePath,
    contexts: contexts,
    isLoading,
    isError,
    error: sourceDirsError,
  } = props;
  const [error, setError] = useState<string>('');
  const [warning, setWarning] = useState<string>('');
  const [analyzeError, setAnalyzeError] = useState<string>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState<boolean>(false);

  let initialContextPaths = [];
  if (!isNullOrUndefined(contexts)) {
    initialContextPaths = contexts.has(dockerfilePath)
      ? contexts.get(dockerfilePath)
      : [];
  } else {
    initialContextPaths = [
      dockerfilePath.split('/').slice(0, -1).join('/').concat('/'),
    ];
  }

  useEffect(() => {
    const delay = setTimeout(async () => {
      setError('');
      setWarning('');
      setContextPathValid(false);
      setAnalyzeError(null);
      if (contextPath != null && contextPath != '') {
        if (contextPath.length === 0 || contextPath.slice(0, 1)[0] !== '/') {
          setError('Path is an invalid context.');
          setContextPathValid(false);
        } else if (!isCustomGit) {
          try {
            setLoadingAnalysis(true);
            const analysis = await analyzeBuildTrigger(
              org,
              repo,
              triggerUuid,
              buildSource,
              contextPath,
              dockerfilePath,
            );
            if (analysis.status === 'warning') {
              setContextPathValid(true);
              setWarning(analysis.message);
            } else if (analysis.status === 'error') {
              setContextPathValid(false);
              setError(analysis.message);
            } else {
              setContextPathValid(true);
            }
            setLoadingAnalysis(false);
          } catch (error) {
            setLoadingAnalysis(false);
            const message =
              error?.response?.data?.error_message || error.toString();
            setAnalyzeError(message);
          }
        } else {
          setContextPathValid(true);
        }
      }
    }, 1000);
    return () => clearTimeout(delay);
  }, [contextPath]);

  if (!isCustomGit && isLoading) {
    return <Spinner />;
  }

  if (isError || !isNullOrUndefined(analyzeError)) {
    const message = isError ? sourceDirsError.toString() : analyzeError;
    return <Alert variant="danger" title={message} />;
  }

  const onChange = (value: string) => {
    if (value.length === 0 || value.slice(0, 1)[0] !== '/') {
      setError('Path is an invalid context.');
      setContextPathValid(false);
    } else {
      setError('');
      setContextPathValid(true);
    }
    setContextPath(value);
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
          <Conditional if={isCustomGit}>
            <TextInput
              isRequired
              type="text"
              id="context-path"
              name="context-path"
              value={contextPath}
              placeholder="/"
              onChange={(_, value) => onChange(value)}
            />
          </Conditional>
          <Conditional
            if={!isCustomGit && !isNullOrUndefined(initialContextPaths)}
          >
            <TypeAheadSelect
              value={contextPath}
              onChange={(value) => onChange(value)}
              initialSelectOptions={initialContextPaths?.map((path, index) => {
                return {
                  key: path,
                  onClick: () => onChange(path),
                  id: `dockerfile-path-option-${index}`,
                  value: path,
                };
              })}
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
  org: string;
  repo: string;
  triggerUuid: string;
  buildSource: string;
  contextPath: string;
  setContextPath: (contextPath: string) => void;
  isCustomGit: boolean;
  setContextPathValid: (contextPathValid: boolean) => void;
  dockerfilePath: string;
  dockerfilePaths: string[];
  isLoading: boolean;
  isError: boolean;
  contexts: Map<string, string[]>;
  error: unknown;
}
