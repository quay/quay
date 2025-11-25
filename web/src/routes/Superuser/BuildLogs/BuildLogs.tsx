import {useState} from 'react';
import {
  PageSection,
  PageSectionVariants,
  Title,
  Form,
  FormGroup,
  TextInput,
  Button,
  Alert,
  Spinner,
  Checkbox,
} from '@patternfly/react-core';
import {useFetchBuildLogsSuperuser} from 'src/hooks/UseBuildLogs';
import {useSuperuserPermissions} from 'src/hooks/UseSuperuserPermissions';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {formatDate, isNullOrUndefined} from 'src/libs/utils';

export default function BuildLogs() {
  const [buildUuid, setBuildUuid] = useState<string>('');
  const [submittedUuid, setSubmittedUuid] = useState<string | null>(null);
  const [showTimestamps, setShowTimestamps] = useState<boolean>(true);

  const {isSuperUser} = useSuperuserPermissions();
  const quayConfig = useQuayConfig();
  const {
    data: build,
    isLoading,
    isError,
    error,
  } = useFetchBuildLogsSuperuser(submittedUuid);

  // Check if BUILD_SUPPORT is enabled
  if (!quayConfig?.features?.BUILD_SUPPORT) {
    return (
      <PageSection variant={PageSectionVariants.light}>
        <Alert variant="warning" title="Build support not enabled">
          Build logs are not available because BUILD_SUPPORT is not enabled in
          the registry configuration.
        </Alert>
      </PageSection>
    );
  }

  // Check if user is superuser
  if (!isSuperUser) {
    return (
      <PageSection variant={PageSectionVariants.light}>
        <Alert variant="danger" title="Access Denied">
          You must be a superuser to access build logs.
        </Alert>
      </PageSection>
    );
  }

  const handleLoadBuild = (e: React.FormEvent) => {
    e.preventDefault();
    if (buildUuid.trim()) {
      setSubmittedUuid(buildUuid.trim());
    }
  };

  const renderBuildInfo = () => {
    if (!build) return null;

    return (
      <div style={{marginTop: '2em'}}>
        <Title headingLevel="h3" size="lg">
          Build Information
        </Title>
        <dl style={{marginTop: '1em'}}>
          <dt>
            <strong>Build UUID:</strong>
          </dt>
          <dd>{isNullOrUndefined(build.uuid) ? build.id : build.uuid}</dd>

          <dt style={{marginTop: '0.5em'}}>
            <strong>Status:</strong>
          </dt>
          <dd>
            {typeof build.status === 'string'
              ? build.status
              : JSON.stringify(build.status)}
          </dd>

          {build.repository && (
            <>
              <dt style={{marginTop: '0.5em'}}>
                <strong>Repository:</strong>
              </dt>
              <dd>
                {build.repository.namespace}/{build.repository.name}
              </dd>
            </>
          )}

          <dt style={{marginTop: '0.5em'}}>
            <strong>Started:</strong>
          </dt>
          <dd>{formatDate(build.started)}</dd>

          {build.completed && (
            <>
              <dt style={{marginTop: '0.5em'}}>
                <strong>Completed:</strong>
              </dt>
              <dd>{formatDate(build.completed)}</dd>
            </>
          )}

          {build.phase && (
            <>
              <dt style={{marginTop: '0.5em'}}>
                <strong>Phase:</strong>
              </dt>
              <dd>{build.phase}</dd>
            </>
          )}

          {build.error && (
            <>
              <dt style={{marginTop: '0.5em'}}>
                <strong>Error:</strong>
              </dt>
              <dd style={{color: '#c9190b'}}>{build.error}</dd>
            </>
          )}
        </dl>
      </div>
    );
  };

  const renderBuildLogs = () => {
    if (!build?.logs || build.logs.length === 0) {
      return (
        <Alert
          variant="info"
          title="No logs available"
          style={{marginTop: '1em'}}
        >
          This build has no logs to display.
        </Alert>
      );
    }

    return (
      <div style={{marginTop: '2em'}}>
        <Title headingLevel="h3" size="lg">
          Build Logs
        </Title>
        <pre
          style={{
            marginTop: '1em',
            backgroundColor: '#f5f5f5',
            padding: '1em',
            borderRadius: '4px',
            overflow: 'auto',
            maxHeight: '600px',
            fontSize: '0.875rem',
            fontFamily: 'monospace',
            lineHeight: '1.5',
          }}
          data-testid="build-logs-display"
        >
          {build.logs.map((log, index) => (
            <div key={index}>
              {showTimestamps && log.timestamp && (
                <span style={{color: '#666', marginRight: '0.5em'}}>
                  [{log.timestamp}]
                </span>
              )}
              {typeof log.message === 'string'
                ? log.message
                : JSON.stringify(log.message)}
            </div>
          ))}
        </pre>
      </div>
    );
  };

  return (
    <>
      {/* Page Header */}
      <PageSection variant={PageSectionVariants.light} hasShadowBottom>
        <Title headingLevel="h1">Build Logs</Title>
      </PageSection>

      {/* Main Content */}
      <PageSection>
        {/* Build UUID Input Form */}
        <Form onSubmit={handleLoadBuild} style={{maxWidth: '600px'}}>
          <FormGroup label="Build UUID" isRequired fieldId="build-uuid">
            <TextInput
              id="build-uuid"
              type="text"
              value={buildUuid}
              onChange={(_event, value) => setBuildUuid(value)}
              placeholder="Enter build UUID"
              data-testid="build-uuid-input"
              aria-label="Build UUID"
            />
          </FormGroup>

          <FormGroup>
            <Checkbox
              id="show-timestamps"
              label="Show timestamps"
              isChecked={showTimestamps}
              onChange={(_event, checked) => setShowTimestamps(checked)}
              data-testid="show-timestamps-checkbox"
              aria-label="Show timestamps in logs"
            />
          </FormGroup>

          <Button
            type="submit"
            variant="primary"
            isDisabled={
              !buildUuid.trim() || (submittedUuid !== null && isLoading)
            }
            data-testid="load-build-button"
          >
            {submittedUuid !== null && isLoading ? 'Loading...' : 'Get Logs'}
          </Button>
        </Form>

        {/* Loading State */}
        {submittedUuid !== null && isLoading && (
          <div style={{marginTop: '2em', textAlign: 'center'}}>
            <Spinner size="lg" aria-label="Loading build logs" />
            <p style={{marginTop: '1em'}}>Loading build logs...</p>
          </div>
        )}

        {/* Error State */}
        {isError && (
          <Alert
            variant="danger"
            title="Cannot find or load build"
            style={{marginTop: '2em', maxWidth: '600px'}}
            data-testid="build-error-alert"
          >
            {error?.message ||
              'The build could not be found or you do not have permission to view it.'}
          </Alert>
        )}

        {/* Success State - Build Info and Logs */}
        {build && !isLoading && (
          <>
            {renderBuildInfo()}
            {renderBuildLogs()}
          </>
        )}
      </PageSection>
    </>
  );
}
